"""Couche de revue par modele : juge ce qu'une regle statique ne peut pas juger
(pertinence des noms, respect des conventions du projet, bug logique, regression)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import List, Optional, Tuple

from model import CRITICAL, MAJOR, MINOR, Finding
from source import SourceFile, git_diff_text

SYSTEM = """Tu es le superviseur de code d'une equipe. Un agent vient de modifier du code.
Tu relis SON diff, pas le reste du depot. Tu ne corriges rien : tu produis un verdict que
l'agent devra traiter.

Tu juges exactement ceci :
1. BUG introduit par le diff : erreur de logique, cas limite casse, contrat d'API rompu,
   comportement different de l'intention declaree, concurrence, nullite, ressource non liberee.
2. REGRESSION : un appelant existant, un test, un schema ou un contrat devient faux.
3. SECURITE : entree non validee, secret expose, autorisation contournee, injection.
4. CONVENTIONS du projet : ce que montrent les fichiers de conventions fournis et le code voisin
   (structure en couches, gestion d'erreur, journalisation, immuabilite, style de test).
5. NOMMAGE : un nom de methode, de classe ou de variable qui ne decrit pas ce qu'il est ou fait,
   qui ment sur son effet, ou qui est incoherent avec le vocabulaire du domaine deja employe.
6. DUPLICATION ou reinvention : le diff reecrit quelque chose qui existe deja dans le depot.
7. COMPLEXITE evitable : methode qui fait plusieurs choses, abstraction inutile, indirection gratuite.

Regles de verdict :
- Severite CRITICAL seulement si le code est faux, dangereux, ou casse l'existant. Ces points
  seront imposes a l'agent : ne mets CRITICAL que si tu es sur, preuve en main.
- MAJOR : defaut reel de qualite a corriger, sans danger immediat.
- MINOR : amelioration souhaitable.
- Pas de remarque de style que l'outillage automatique traite deja (espaces, longueur de ligne).
- Pas de remarque sur du code non touche par le diff, sauf si le diff le casse.
- Si tu ne trouves rien de solide, renvoie une liste vide. Un faux positif coute plus cher
  qu'un oubli : il envoie l'agent modifier du code correct.

Tu reponds UNIQUEMENT par un objet JSON, sans texte autour, de la forme :
{"findings":[{"severity":"CRITICAL|MAJOR|MINOR","category":"bug|securite|duplication|complexite|nommage|convention","file":"chemin/relatif","line":123,"symbol":"Classe.methode","message":"ce qui est faux, une phrase","fix":"l'action precise a faire","evidence":"la ligne ou l'extrait concerne"}],"verdict":"une phrase de synthese"}
"""

PROMPT = """## Conventions du projet
{conventions}

## Fichiers modifies
{files}

## Constats de l'analyse statique (deja detectes, ne les repete pas)
{static}

## Diff a relire
```diff
{diff}
```

Tu peux lire des fichiers du depot avec tes outils pour verifier un appelant, un test ou une
convention avant de te prononcer. Fais-le pour tout point que tu veux classer CRITICAL.
Puis reponds par le seul objet JSON demande.
"""

CAT_MAP = {
    "bug": "bug", "securite": "securite", "security": "securite",
    "duplication": "duplication", "complexite": "complexite", "complexity": "complexite",
    "nommage": "nommage", "naming": "nommage", "convention": "convention",
    "conventions": "convention",
}


def available(cfg) -> Optional[str]:
    if not cfg.llm.get("enabled", True):
        return None
    if os.environ.get("SUPERVISOR_NO_LLM"):
        return None
    cli = cfg.llm.get("cli") or "claude"
    return shutil.which(cli) or (cli if os.path.isfile(cli) else None)


def _read_head(path: str, limit: int) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None  # fichier illisible : il est ignore, la revue continue sans lui


def _conventions(root: str, cfg) -> str:
    blocks = []
    for name in cfg.llm.get("convention_files", []):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        content = _read_head(path, 6000)
        if content is None:
            continue
        blocks.append("### %s\n%s" % (name, content))
        if len(blocks) >= 3:
            break
    return "\n\n".join(blocks) if blocks else "(aucun fichier de conventions trouve : deduis les conventions du code voisin)"


def review(root: str, files: List[SourceFile], static_findings: List[Finding], cfg) -> Tuple[List[Finding], str]:
    exe = available(cfg)
    if not exe or not files:
        return [], ""
    budget = cfg.llm.get("max_diff_chars", 60000)
    diff = git_diff_text(root, [sf.path for sf in files], budget)
    # Un fichier neuf n'apparait pas dans `git diff` : on fournit son contenu tel quel.
    diff += _new_file_blocks(files, diff, budget - len(diff))
    if not diff.strip():
        return [], ""
    top = static_findings[: cfg.llm.get("max_static_findings_in_prompt", 25)]
    static_txt = "\n".join("- [%s] %s %s : %s" % (f.severity, f.rule, f.location(), f.message) for f in top) or "(aucun)"
    prompt = PROMPT.format(
        conventions=_conventions(root, cfg),
        files="\n".join("- %s%s" % (sf.path, " (nouveau)" if sf.is_new else "") for sf in files),
        static=static_txt,
        diff=diff,
    )
    cmd = [
        exe, "-p",
        "--model", cfg.llm.get("model", "sonnet"),
        "--append-system-prompt", SYSTEM,
        "--allowedTools", "Read,Grep,Glob",
        "--permission-mode", "dontAsk",
        "--output-format", "json",
    ]
    env = dict(os.environ)
    env["CLAUDE_CODE_DISABLE_HOOKS"] = "1"       # le relecteur ne doit pas redeclencher le hook
    env["SUPERVISOR_ACTIVE"] = "1"
    try:
        # Le prompt passe par l'entree standard : en argument, un diff de quelques dizaines de milliers
        # de caracteres depasse la limite de ligne de commande de Windows (WinError 206).
        proc = subprocess.run(cmd, input=prompt.encode("utf-8"), cwd=root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=cfg.llm.get("timeout_seconds", 180), env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], "revue LLM indisponible (%s)" % exc
    raw = proc.stdout.decode("utf-8", "replace")
    payload = _extract_result(raw)
    if payload is None:
        return [], "revue LLM sans resultat exploitable"
    findings = []
    for item in payload.get("findings", [])[:30]:
        sev = str(item.get("severity", MAJOR)).upper()
        if sev not in (CRITICAL, MAJOR, MINOR):
            sev = MAJOR
        cat = CAT_MAP.get(str(item.get("category", "")).lower(), "convention")
        path = str(item.get("file") or (files[0].path if files else ""))
        findings.append(Finding(
            rule="LLM.%s" % cat.upper(), category=cat, severity=sev,
            message=str(item.get("message", "")).strip()[:500],
            fix=str(item.get("fix", "")).strip()[:800],
            file=path.replace("\\", "/"),
            line=_as_int(item.get("line")),
            symbol=(str(item.get("symbol")) if item.get("symbol") else None),
            evidence=str(item.get("evidence", ""))[:300],
            source="llm",
        ))
    return findings, str(payload.get("verdict", ""))[:400]


def _new_file_blocks(files: List[SourceFile], diff: str, budget: int) -> str:
    if budget <= 0:
        return ""
    blocks = []
    for sf in files:
        if ("b/" + sf.path) in diff:
            continue
        head = "\n".join("+" + l for l in sf.lines[:400])
        block = "\n--- /dev/null\n+++ b/%s\n@@ fichier entier @@\n%s\n" % (sf.path, head)
        if len(block) > budget:
            break
        blocks.append(block)
        budget -= len(block)
    return "".join(blocks)


def _as_int(value) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _load_json(text: str):
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return None  # pas du JSON (texte libre autour de la reponse) : l'appelant cherche plus loin


def _extract_result(raw: str):
    """La sortie de `claude -p --output-format json` enveloppe la reponse dans .result."""
    text = raw.strip()
    if not text:
        return None
    envelope = _load_json(text)
    if isinstance(envelope, dict):
        if "findings" in envelope:
            return envelope
        inner = envelope.get("result") or envelope.get("content") or ""
        if isinstance(inner, list):
            inner = " ".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in inner)
        text = str(inner)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        text = text[start:end + 1]
    parsed = _load_json(text)
    return parsed if isinstance(parsed, dict) else None
