"""Orchestration des analyses statiques."""
from __future__ import annotations

import os
import shlex
import subprocess
import time
from typing import List, Tuple

import rules_bugs
import rules_duplication
import rules_naming
import rules_quality
import rules_security
from model import CRITICAL, MAJOR, MINOR, SEVERITY_ORDER, Finding, dedupe, sort_findings
from source import (SourceFile, extract_functions, git_changed_files, git_changed_lines,
                    is_structural, load)


def select_files(root: str, cfg, touched_hint=None) -> Tuple[List[SourceFile], List[str]]:
    """Fichiers a analyser : etat git, croise avec les fichiers touches dans la session."""
    changed, new = git_changed_files(root)
    if touched_hint:
        for p in touched_hint:
            rel = _relativize(root, p)
            if rel:
                changed.add(rel)
                if rel not in changed:
                    new.add(rel)
    candidates = sorted(p for p in changed if not cfg.is_excluded(p) and not cfg.is_quiet(p))
    candidates = [p for p in candidates if _is_code(p)]
    if len(candidates) > cfg["max_files"]:
        candidates = candidates[: cfg["max_files"]]
    line_map = git_changed_lines(root, candidates)
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
    except Exception:
        return None


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
        try:
            findings.extend(rules_duplication.check(files, root, cfg))
        except Exception:
            pass
    findings.extend(run_external_tools(root, files, cfg))
    return sort_findings(dedupe(findings))


def run_external_tools(root: str, files: List[SourceFile], cfg) -> List[Finding]:
    """Outils du projet declares explicitement dans la configuration.
    Aucun outil n'est lance si la liste est vide (cas par defaut)."""
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
        if not selected:
            continue
        rendered = cmd.replace("{files}", " ".join(shlex.quote(p) for p in selected))
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
    res = {CRITICAL: 0, MAJOR: 0, MINOR: 0}
    for f in findings:
        res[f.severity] = res.get(f.severity, 0) + 1
    return res
