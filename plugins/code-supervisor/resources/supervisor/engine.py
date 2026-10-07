"""Orchestration des analyses statiques."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from typing import List, Tuple

import rules_bugs
import rules_duplication
import rules_naming
import rules_quality
import rules_security
from model import CRITICAL, MAJOR, MINOR, SEVERITY_ORDER, Finding, dedupe, sort_findings
from source import (SourceFile, content_fingerprint, extract_functions, git_changed_files, git_changed_lines,
                    git_files_since, git_root, is_structural, load)


def select_files(root: str, cfg, touched_hint=None, base_ref=None,
                 reviewed=None) -> Tuple[List[SourceFile], List[str]]:
    """Fichiers a analyser : l'etat git, plus ce qui a ete commite depuis `base_ref`.

    Les fichiers ecrits pendant la session (transcript) ne comptent que hors d'un depot git. Dans un depot,
    un fichier deja commite et inchange n'a plus rien a faire relire : le reprendre ici le ferait analyser
    en entier a chaque passe, avec les memes constats, jusqu'a la fin de la session.

    `reviewed` associe un chemin a l'empreinte de son contenu lors d'une passe precedente sans blocage : un fichier
    dont le contenu n'a pas change depuis n'est pas relu, qu'il ait ete commite entre-temps ou non."""
    changed, new = git_changed_files(root)
    if base_ref:
        changed |= git_files_since(root, base_ref)
    if touched_hint and git_root(root) is None:
        for p in touched_hint:
            rel = _relativize(root, p)
            if rel:
                changed.add(rel)
    candidates = sorted(p for p in changed if not cfg.is_excluded(p) and not cfg.is_quiet(p))
    candidates = [p for p in candidates if _is_code(p)]
    if reviewed:
        candidates = [p for p in candidates if reviewed.get(p) != content_fingerprint(root, p)]
    if len(candidates) > cfg["max_files"]:
        candidates = candidates[: cfg["max_files"]]
    line_map = git_changed_lines(root, candidates, base_ref)
    files = load(root, candidates, changed_lines=line_map, new_files=new)
    return files, candidates


def _is_code(path: str) -> bool:
    from source import lang_of
    return lang_of(path) is not None


def _relativize(root: str, path: str):
    try:
        p = os.path.abspath(path)
        r = os.path.abspath(root)
        if not p.lower().startswith(r.lower()):
            return None
        return os.path.relpath(p, r).replace("\\", "/")
    except (OSError, TypeError, ValueError):     # chemin qui n'en est pas un, ou sur un autre lecteur
        return None


def _duplication_findings(files: List[SourceFile], root: str, cfg) -> List[Finding]:
    """La duplication est une passe optionnelle : sa panne ne doit pas faire echouer l'analyse,
    mais elle est signalee au lieu d'etre avalee."""
    try:
        return rules_duplication.check(files, root, cfg)
    except Exception as exc:  # frontiere d'une passe optionnelle
        sys.stderr.write("superviseur : analyse de duplication abandonnee (%s)\n" % exc)
        return []


def analyze(root: str, files: List[SourceFile], cfg) -> List[Finding]:
    deadline = time.time() + cfg["time_budget_seconds"]
    findings: List[Finding] = []
    for sf in files:
        if time.time() > deadline:
            break
        findings.extend(rules_security.check(sf))
        findings.extend(rules_bugs.check_lines(sf))
        findings.extend(rules_bugs.check_blocks(sf))
        findings.extend(rules_quality.check_file(sf, cfg))
        findings.extend(rules_quality.check_unused_imports(sf))
        if is_structural(sf.path):
            functions = extract_functions(sf)
            findings.extend(rules_quality.check_functions(sf, functions, cfg))
            findings.extend(rules_bugs.check_function_bugs(sf, functions))
            findings.extend(rules_naming.check_identifiers(sf, functions))
    if time.time() < deadline:
        findings.extend(_duplication_findings(files, root, cfg))
    findings.extend(run_external_tools(root, files, cfg))
    return sort_findings(dedupe(findings))


# Caracteres d'un nom de fichier qu'aucun quoting ne neutralise de facon fiable dans cmd.exe :
# separateurs de commandes, redirections, expansion de variables (`%`) et de `!`.
_CMD_UNSAFE_CHARS = frozenset('"%^&|<>!')


def quote_path(path: str, windows: bool = os.name == "nt"):
    """Nom de fichier pret a etre insere dans une ligne de commande, ou None s'il ne peut pas l'etre.

    `shlex.quote` produit un quoting POSIX : sous cmd.exe, les guillemets simples ne protegent rien et
    un nom comme `a&b.py` (valide sous Windows) separerait la commande. Sous Windows on met donc le nom
    entre guillemets doubles et on refuse ceux qui contiennent un caractere que cmd.exe interprete
    meme entre guillemets."""
    if not windows:
        return shlex.quote(path)
    if any(c in _CMD_UNSAFE_CHARS or ord(c) < 32 for c in path):
        return None
    return '"%s"' % path


def _quote_files(tool_name: str, paths: List[str]) -> List[str]:
    quoted = []
    for path in paths:
        q = quote_path(path)
        if q is None:
            sys.stderr.write("superviseur : %s ignore par l'outil %s (nom incompatible avec une ligne de commande)\n"
                             % (path, tool_name))
        else:
            quoted.append(q)
    return quoted


def run_external_tools(root: str, files: List[SourceFile], cfg) -> List[Finding]:
    """Outils du projet declares explicitement dans la configuration.
    Aucun outil n'est lance si la liste est vide (cas par defaut).

    La commande passe par un shell (`shell=True`), a dessein. Elle est ecrite par l'utilisateur dans sa
    propre configuration : c'est la meme confiance que la commande du hook dans settings.json. Une liste
    d'arguments sans shell n'aiderait pas ici : sous Windows, `npx` et `mvn` sont des scripts `.cmd`,
    que cmd.exe interprete de la meme facon (un nom `a&ver` y executerait `ver`, `%COMSPEC%` y serait
    developpe), et on perdrait `&&`, les redirections et les variables des commandes declarees. Ce qui
    vient du depot supervise, les noms de fichiers, ne passe que par `quote_path`, dont l'auto-test
    verifie de bout en bout (`_external_tool_problems`) qu'aucun nom n'execute quoi que ce soit.
    Le constat « appel systeme avec shell=True » du superviseur sur cette ligne est donc connu et accepte."""
    out: List[Finding] = []
    tools = cfg.get("external_tools") or []
    if not tools:
        return out
    paths = [sf.path for sf in files]
    for tool in tools:
        name = tool.get("name", "outil")
        cmd = tool.get("command")
        if not cmd:
            continue
        exts = tool.get("extensions")
        selected = [p for p in paths if (not exts or os.path.splitext(p)[1].lower() in exts)]
        quoted = _quote_files(name, selected)
        if not quoted:
            continue
        # La commande vient de la configuration de l'utilisateur, donc de confiance ; les noms de
        # fichiers, eux, viennent du depot supervise : ils ne passent que par _quote_files.
        rendered = cmd.replace("{files}", " ".join(quoted))
        try:
            proc = subprocess.run(rendered, cwd=root, shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=tool.get("timeout_seconds", 120))
            output = proc.stdout.decode("utf-8", "replace").strip()
        except Exception as exc:
            out.append(Finding(
                rule="TOOL.%s.ERROR" % name.upper(), category="convention", severity=MINOR,
                message="L'outil %s n'a pas pu etre execute (%s)." % (name, exc),
                fix="Verifier la commande declaree dans supervisor.config.json.",
                file=selected[0], source="tool"))
            continue
        failed = proc.returncode != 0
        if failed and output:
            out.append(Finding(
                rule="TOOL.%s" % name.upper(), category=tool.get("category", "convention"),
                severity=tool.get("severity", MAJOR),
                message="%s signale des problemes." % name,
                fix="Corriger les points remontes par %s :\n%s" % (name, output[:4000]),
                file=selected[0], source="tool", evidence=output[:400]))
    return out


def blocking(findings: List[Finding], cfg) -> List[Finding]:
    levels = set(cfg["block_on_severity"])
    never = set(cfg["never_block_categories"])
    return [f for f in findings if f.severity in levels and f.category not in never]


def counts(findings: List[Finding]) -> dict:
    per_severity = {CRITICAL: 0, MAJOR: 0, MINOR: 0}
    for finding in findings:
        per_severity[finding.severity] = per_severity.get(finding.severity, 0) + 1
    return per_severity
