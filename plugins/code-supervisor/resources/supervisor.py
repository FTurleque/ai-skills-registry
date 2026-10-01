#!/usr/bin/env python3
"""Superviseur de code — hook Stop / SubagentStop de Claude Code.

Se declenche quand un agent a fini d'implementer. Relit uniquement ce qui a change,
croise une analyse statique portable et une relecture par modele, puis renvoie
l'agent corriger si un probleme bloquant est trouve.

Usages :
  echo '<payload>' | python3 supervisor.py          # mode hook (stdin JSON)
  python3 supervisor.py --check [chemins...]        # relecture manuelle, sortie lisible
  python3 supervisor.py --self-test                 # verifie le moteur sur les fixtures
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "supervisor"))

import engine                      # noqa: E402
import llm                          # noqa: E402
import report as report_mod         # noqa: E402
from config import load_config      # noqa: E402
from model import CRITICAL, Finding, sort_findings  # noqa: E402
from source import git_root         # noqa: E402

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "StrReplace", "create_file"}


# --------------------------------------------------------------------------- etat

def state_path(log_dir: str, session_id: str) -> str:
    return os.path.join(log_dir, "state-%s.json" % (session_id or "unknown")[:40])


def read_state(path: str) -> dict:
    default = {"rounds_by_signature": {}, "released_signatures": []}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data.setdefault("rounds_by_signature", {})
            data.setdefault("released_signatures", [])
            return data
    except Exception:
        pass
    return default


def write_state(path: str, state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass


# --------------------------------------------------------------------------- transcript

def touched_files(transcript_path: str, limit_lines: int = 4000):
    """Fichiers ecrits par l'agent pendant la session, lus depuis le transcript."""
    paths = []
    if not transcript_path or not os.path.isfile(transcript_path):
        return paths
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[-limit_lines:]
    except Exception:
        return paths
    for line in lines:
        if '"tool_use"' not in line and "file_path" not in line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        for block in _iter_blocks(entry):
            if block.get("type") != "tool_use":
                continue
            if block.get("name") not in EDIT_TOOLS:
                continue
            inp = block.get("input") or {}
            for key in ("file_path", "path", "notebook_path"):
                if inp.get(key):
                    paths.append(inp[key])
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _iter_blocks(entry):
    msg = entry.get("message") if isinstance(entry, dict) else None
    content = (msg or {}).get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                yield block


# --------------------------------------------------------------------------- analyse

def run(project_dir: str, cfg, session_id: str, hints, round_no: int):
    root = git_root(project_dir) or project_dir
    files, candidates = engine.select_files(root, cfg, touched_hint=hints)
    if not files:
        return None
    static = engine.analyze(root, files, cfg)
    llm_findings, verdict = llm.review(root, files, static, cfg)
    findings = sort_findings(static + llm_findings)
    counts = engine.counts(findings)
    blockers = engine.blocking(findings, cfg)
    others = [f for f in findings if f not in blockers]
    return {
        "root": root, "files": files, "findings": findings, "counts": counts,
        "blockers": blockers, "others": others, "verdict": verdict,
    }


def log_dir_for(project_dir: str, cfg) -> str:
    d = cfg.get("log_dir") or os.environ.get("SUPERVISOR_LOG_DIR") \
        or os.path.join(project_dir, ".claude", "supervisor")
    os.makedirs(d, exist_ok=True)
    return d


# --------------------------------------------------------------------------- mode hook

def hook_main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    # Anti-boucle : Claude Code repasse avec ce drapeau quand il est temps de s'arreter.
    if payload.get("stop_hook_active"):
        return 0
    # Le relecteur lance par le hook ne doit pas se superviser lui-meme.
    if os.environ.get("SUPERVISOR_ACTIVE"):
        return 0
    if (payload.get("agent_type") or "") in ("code-supervisor", "supervisor"):
        return 0

    project_dir = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    user_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    cfg = load_config(project_dir, user_dir, HERE)
    if not cfg["enabled"]:
        return 0

    session_id = str(payload.get("session_id") or "")
    logs = log_dir_for(project_dir, cfg)
    st_path = state_path(logs, session_id)
    state = read_state(st_path)
    round_no = int(state.get("rounds", 0)) + 1

    hints = touched_files(payload.get("transcript_path", ""))
    started = time.time()
    result = run(project_dir, cfg, session_id, hints, round_no)
    if result is None:
        return 0

    blockers = result["blockers"]
    others = result["others"]
    keys = sorted(f.key() for f in blockers)
    # Un meme lot de problemes ne peut renvoyer l'agent au travail qu'un nombre borne de fois.
    # Passe ce seuil, l'empreinte est liberee : le superviseur avertit mais ne bloque plus,
    # pour que la session ne tourne pas en rond sur un point que l'agent ne sait pas corriger.
    signature = hashlib.sha1("|".join(keys).encode("utf-8")).hexdigest()[:16] if keys else ""
    rounds_by_sig = state["rounds_by_signature"]
    released = set(state["released_signatures"])
    seen_rounds = int(rounds_by_sig.get(signature, 0))
    exhausted = signature in released or seen_rounds >= int(cfg["max_block_rounds"])

    report_file = os.path.join(logs, "rapport-%s.md" % time.strftime("%Y%m%d-%H%M%S"))
    limit = int(cfg["max_findings_in_report"])
    blocked = bool(blockers) and not exhausted

    try:
        with open(report_file, "w", encoding="utf-8") as fh:
            fh.write(report_mod.full_report(result["findings"], result["files"], result["counts"],
                                            result["verdict"], blocked, session_id, round_no))
    except Exception:
        report_file = "(rapport non ecrit)"

    if blocked:
        rounds_by_sig[signature] = seen_rounds + 1
        if rounds_by_sig[signature] >= int(cfg["max_block_rounds"]):
            released.add(signature)       # prochaine fois : avertissement, plus de blocage
    state["rounds_by_signature"] = dict(list(rounds_by_sig.items())[-30:])
    state["released_signatures"] = sorted(released)[-30:]
    state["rounds"] = round_no
    state["duration"] = round(time.time() - started, 1)
    write_state(st_path, state)

    summary = report_mod.user_summary(result["counts"], blocked, len(result["files"]))

    if blocked:
        out = {
            "decision": "block",
            "reason": report_mod.block_message(blockers, others, result["verdict"], report_file, limit),
            "systemMessage": summary,
        }
    elif result["findings"]:
        detail = report_mod.warn_message(result["findings"], result["verdict"], report_file, limit)
        if blockers and exhausted:
            detail = ("Des problemes bloquants subsistent apres %d passe(s) de correction : "
                      "le superviseur rend la main pour eviter une boucle. A arbitrer manuellement.\n\n"
                      % max(seen_rounds, 1)) + detail
            summary += " Blocage leve apres %d passe(s) : a verifier manuellement." % max(seen_rounds, 1)
        out = {
            "hookSpecificOutput": {"hookEventName": payload.get("hook_event_name", "Stop"),
                                   "additionalContext": detail},
            "systemMessage": summary,
        }
    else:
        out = {"systemMessage": summary}

    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- mode manuel

def cli_main(argv) -> int:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    user_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    cfg = load_config(project_dir, user_dir, HERE)
    explicit = [a for a in argv if not a.startswith("-")]
    root = git_root(project_dir) or project_dir
    if explicit:
        from source import git_changed_lines, load
        rels = []
        for p in explicit:
            ap = os.path.abspath(p)
            rels.append(os.path.relpath(ap, root).replace("\\", "/"))
        files = load(root, rels, changed_lines=git_changed_lines(root, rels))
        findings = engine.analyze(root, files, cfg)
        verdict = ""
        if "--llm" in argv:
            extra, verdict = llm.review(root, files, findings, cfg)
            findings = sort_findings(findings + extra)
    else:
        result = run(project_dir, cfg, "manuel", None, 1)
        if result is None:
            print("Aucun fichier modifie a relire.")
            return 0
        files, findings, verdict = result["files"], result["findings"], result["verdict"]
    counts = engine.counts(findings)
    blockers = engine.blocking(findings, cfg)
    print(report_mod.full_report(findings, files, counts, verdict, bool(blockers), "manuel", 1))
    return 1 if blockers else 0


def self_test() -> int:
    fixtures = next((d for d in (os.path.join(HERE, "fixtures"),
                                 os.path.join(os.path.dirname(HERE), "fixtures"))
                     if os.path.isdir(d)), None)
    if not fixtures:
        print("Dossier fixtures absent (cherche dans %s et son parent)." % HERE)
        return 1
    from config import Config, DEFAULTS
    from source import load
    cfg = Config(json.loads(json.dumps(DEFAULTS)))
    rels = sorted(f for f in os.listdir(fixtures) if not f.startswith("."))
    files = load(fixtures, rels)
    findings = engine.analyze(fixtures, files, cfg)
    by_rule = {}
    for f in findings:
        by_rule.setdefault(f.rule, 0)
        by_rule[f.rule] += 1
    print("Fichiers analyses : %d" % len(files))
    print("Constats : %d" % len(findings))
    for rule in sorted(by_rule):
        print("  %-28s %d" % (rule, by_rule[rule]))
    expected = {
        "SEC.HARDCODED_SECRET", "SEC.SQL_CONCAT", "SEC.WEAK_HASH", "SEC.TLS_DISABLED",
        "BUG.CATCH_SWALLOWED", "BUG.STRING_IDENTITY", "BUG.STATIC_DATEFORMAT",
        "CPX.CYCLOMATIC_HIGH", "NAM.VAGUE_VARIABLE", "NAM.VAGUE_METHOD", "DUP.BLOCK",
    }
    missing = sorted(expected - set(by_rule))
    if missing:
        print("\nECHEC — regles attendues non declenchees : %s" % ", ".join(missing))
        return 1
    print("\nOK — toutes les regles attendues se declenchent.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--self-test" in args:
        sys.exit(self_test())
    if "--check" in args:
        sys.exit(cli_main([a for a in args if a != "--check"]))
    sys.exit(hook_main())
