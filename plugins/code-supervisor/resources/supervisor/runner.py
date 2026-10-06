"""Logique du superviseur : hook Stop / SubagentStop, mode manuel et auto-test.

Chargee par `supervisor.py`, qui place ce dossier sur le chemin d'import."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import time

import engine
import llm
import report as report_mod
from config import DEFAULTS, Config, load_config
from model import sort_findings
from source import git_changed_lines, git_root, load

# Dossier de `supervisor.py` : configuration livree a cote du script et fixtures de l'auto-test.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "StrReplace", "create_file"}
PATH_KEYS = ("file_path", "path", "notebook_path")
SUPERVISOR_AGENTS = ("code-supervisor", "supervisor")
DEFAULT_LOG_SUBDIR = os.path.join("docs", "rapport-supervisor")
STATE_HISTORY = 30          # empreintes conservees dans l'etat anti-boucle
TRANSCRIPT_TAIL_LINES = 4000


# --------------------------------------------------------------------------- etat

def state_path(log_dir: str, session_id: str) -> str:
    return os.path.join(log_dir, "state-%s.json" % (session_id or "unknown")[:40])


def read_state(path: str) -> dict:
    default = {"rounds_by_signature": {}, "released_signatures": []}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
    except (OSError, ValueError):
        return default  # etat absent (premier passage) ou JSON corrompu : on repart d'un etat vierge
    if not isinstance(stored, dict):
        return default
    stored.setdefault("rounds_by_signature", {})
    stored.setdefault("released_signatures", [])
    return stored


def write_state(path: str, state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except (OSError, TypeError, ValueError) as exc:
        # L'etat anti-boucle est un confort : son echec ne doit pas faire echouer le hook.
        sys.stderr.write("superviseur : etat non ecrit (%s)\n" % exc)


# --------------------------------------------------------------------------- transcript

def _parse_json_line(line: str):
    try:
        return json.loads(line)
    except ValueError:
        return None  # ligne de transcript tronquee ou qui n'est pas du JSON : on l'ignore


def _read_tail(path: str, limit_lines: int):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.readlines()[-limit_lines:]
    except OSError:
        return []  # transcript illisible : aucun indice de fichier, la relecture se fait sur git


def _iter_blocks(entry):
    msg = entry.get("message") if isinstance(entry, dict) else None
    content = (msg or {}).get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                yield block


def _edited_paths(entry):
    for block in _iter_blocks(entry):
        if block.get("type") != "tool_use" or block.get("name") not in EDIT_TOOLS:
            continue
        tool_input = block.get("input") or {}
        for key in PATH_KEYS:
            if tool_input.get(key):
                yield tool_input[key]


def touched_files(transcript_path: str, limit_lines: int = TRANSCRIPT_TAIL_LINES):
    """Fichiers ecrits par l'agent pendant la session, lus depuis le transcript."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return []
    paths = []
    for line in _read_tail(transcript_path, limit_lines):
        if '"tool_use"' not in line and "file_path" not in line:
            continue
        entry = _parse_json_line(line)
        if entry is not None:
            paths.extend(_edited_paths(entry))
    return list(dict.fromkeys(paths))


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


def _write_self_ignore(directory: str) -> None:
    """Un rapport n'a pas vocation a etre commite : le dossier s'ignore lui-meme (le `*` couvre
    aussi ce .gitignore), sans toucher au .gitignore du projet supervise."""
    ignore = os.path.join(directory, ".gitignore")
    if os.path.exists(ignore):
        return
    try:
        with open(ignore, "w", encoding="utf-8") as fh:
            fh.write("*\n")
    except OSError as err:
        sys.stderr.write("supervisor : %s non ecrit (%s) ; les rapports pourraient etre commites\n"
                         % (ignore, err))


def log_dir_for(project_dir: str, cfg) -> str:
    directory = cfg.get("log_dir") or os.environ.get("SUPERVISOR_LOG_DIR") \
        or os.path.join(project_dir, DEFAULT_LOG_SUBDIR)
    os.makedirs(directory, exist_ok=True)
    _write_self_ignore(directory)
    return directory


# --------------------------------------------------------------------------- mode hook

def _read_payload():
    """Charge utile du hook sur l'entree standard, ou None si elle est absente ou invalide."""
    if sys.stdin is None:
        return None
    try:
        # Claude Code envoie de l'UTF-8 ; `json.load(sys.stdin)` decoderait avec la page de codes de
        # Windows (cp1252) et deformerait un chemin accentue, rendant le depot introuvable.
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except (OSError, ValueError, RecursionError):
        return None
    return payload if isinstance(payload, dict) else None


def _must_skip(payload: dict) -> bool:
    # Anti-boucle : Claude Code repasse avec ce drapeau quand il est temps de s'arreter.
    if payload.get("stop_hook_active"):
        return True
    # Le relecteur lance par le hook ne doit pas se superviser lui-meme.
    if os.environ.get("SUPERVISOR_ACTIVE"):
        return True
    return (payload.get("agent_type") or "") in SUPERVISOR_AGENTS


def _blockers_signature(blockers) -> str:
    keys = sorted(f.key() for f in blockers)
    return hashlib.sha256("|".join(keys).encode("utf-8")).hexdigest()[:16] if keys else ""


def _round_status(state: dict, signature: str, max_rounds: int):
    """(nombre de passes deja faites pour ce lot de problemes, lot libere ou non).

    Un meme lot de problemes ne peut renvoyer l'agent au travail qu'un nombre borne de fois.
    Passe ce seuil, l'empreinte est liberee : le superviseur avertit mais ne bloque plus,
    pour que la session ne tourne pas en rond sur un point que l'agent ne sait pas corriger."""
    seen_rounds = int(state["rounds_by_signature"].get(signature, 0))
    exhausted = signature in set(state["released_signatures"]) or seen_rounds >= max_rounds
    return seen_rounds, exhausted


def _record_round(state: dict, signature: str, blocked: bool, seen_rounds: int,
                  max_rounds: int, round_no: int, started: float) -> None:
    rounds_by_signature = state["rounds_by_signature"]
    released = set(state["released_signatures"])
    if blocked:
        rounds_by_signature[signature] = seen_rounds + 1
        if rounds_by_signature[signature] >= max_rounds:
            released.add(signature)       # prochaine fois : avertissement, plus de blocage
    state["rounds_by_signature"] = dict(list(rounds_by_signature.items())[-STATE_HISTORY:])
    state["released_signatures"] = sorted(released)[-STATE_HISTORY:]
    state["rounds"] = round_no
    state["duration"] = round(time.time() - started, 1)


def _write_report(logs: str, result: dict, blocked: bool, session_id: str, round_no: int) -> str:
    report_file = os.path.join(logs, "rapport-%s.md" % time.strftime("%Y%m%d-%H%M%S"))
    try:
        text = report_mod.full_report(result["findings"], result["files"], result["counts"],
                                      result["verdict"], blocked, session_id, round_no)
        with open(report_file, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception as exc:  # frontiere du hook : un rapport manque ne doit pas annuler le verdict
        sys.stderr.write("superviseur : rapport non ecrit (%s)\n" % exc)
        return "(rapport non ecrit)"
    return report_file


def _encode_hook_output(out: dict) -> str:
    """ASCII pur (accents echappes en \\uXXXX) : toujours encodable, quel que soit l'encodage de stdout."""
    return json.dumps(out)


def _hook_output(payload: dict, result: dict, blocked: bool, exhausted: bool,
                 seen_rounds: int, report_file: str, limit: int) -> dict:
    blockers = result["blockers"]
    summary = report_mod.user_summary(result["counts"], blocked, len(result["files"]))
    if blocked:
        return {
            "decision": "block",
            "reason": report_mod.block_message(blockers, result["others"], result["verdict"], report_file, limit),
            "systemMessage": summary,
        }
    if not result["findings"]:
        return {"systemMessage": summary}
    detail = report_mod.warn_message(result["findings"], result["verdict"], report_file, limit)
    if blockers and exhausted:
        passes = max(seen_rounds, 1)
        detail = ("Des problemes bloquants subsistent apres %d passe(s) de correction : "
                  "le superviseur rend la main pour eviter une boucle. A arbitrer manuellement.\n\n"
                  % passes) + detail
        summary += " Blocage leve apres %d passe(s) : a verifier manuellement." % passes
    return {
        "hookSpecificOutput": {"hookEventName": payload.get("hook_event_name", "Stop"),
                               "additionalContext": detail},
        "systemMessage": summary,
    }


def hook_main() -> int:
    payload = _read_payload()
    if payload is None or _must_skip(payload):
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

    started = time.time()
    result = run(project_dir, cfg, session_id, touched_files(payload.get("transcript_path", "")), round_no)
    if result is None:
        return 0

    max_rounds = int(cfg["max_block_rounds"])
    signature = _blockers_signature(result["blockers"])
    seen_rounds, exhausted = _round_status(state, signature, max_rounds)
    blocked = bool(result["blockers"]) and not exhausted

    report_file = _write_report(logs, result, blocked, session_id, round_no)
    _record_round(state, signature, blocked, seen_rounds, max_rounds, round_no, started)
    write_state(st_path, state)

    limit = int(cfg["max_findings_in_report"])
    out = _hook_output(payload, result, blocked, exhausted, seen_rounds, report_file, limit)
    sys.stdout.write(_encode_hook_output(out))
    return 0


# --------------------------------------------------------------------------- mode manuel

def _review_explicit(argv, explicit, root: str, cfg):
    rels = [os.path.relpath(os.path.abspath(p), root).replace("\\", "/") for p in explicit]
    files = load(root, rels, changed_lines=git_changed_lines(root, rels))
    findings = engine.analyze(root, files, cfg)
    verdict = ""
    if "--llm" in argv:
        extra, verdict = llm.review(root, files, findings, cfg)
        findings = sort_findings(findings + extra)
    return files, findings, verdict


def cli_main(argv) -> int:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    user_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    cfg = load_config(project_dir, user_dir, HERE)
    explicit = [a for a in argv if not a.startswith("-")]
    root = git_root(project_dir) or project_dir
    if explicit:
        files, findings, verdict = _review_explicit(argv, explicit, root, cfg)
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


# --------------------------------------------------------------------------- auto-test

EXPECTED_RULES = {
    "SEC.HARDCODED_SECRET", "SEC.SQL_CONCAT", "SEC.WEAK_HASH", "SEC.TLS_DISABLED",
    "BUG.CATCH_SWALLOWED", "BUG.STRING_IDENTITY", "BUG.STATIC_DATEFORMAT",
    "CPX.CYCLOMATIC_HIGH", "NAM.VAGUE_VARIABLE", "NAM.VAGUE_METHOD", "DUP.BLOCK",
    "BUG.SUPPRESS",
}
# Les fixtures clean_* citent des marqueurs de suppression ou des nombres sans en etre :
# ces regles ne doivent pas s'y declencher (faux positifs).
FALSE_POSITIVE_RULES = {"BUG.SUPPRESS", "CNV.MAGIC_NUMBER"}


def _fixtures_dir():
    candidates = (os.path.join(HERE, "fixtures"), os.path.join(os.path.dirname(HERE), "fixtures"))
    return next((d for d in candidates if os.path.isdir(d)), None)


def _print_findings_by_rule(files, findings) -> set:
    by_rule = {}
    for f in findings:
        by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
    print("Fichiers analyses : %d" % len(files))
    print("Constats : %d" % len(findings))
    for rule in sorted(by_rule):
        print("  %-28s %d" % (rule, by_rule[rule]))
    return set(by_rule)


def _write_json(path: str, content: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(content, fh)


def _project_config_problems() -> list:
    """Une configuration de projet hostile ne doit fixer ni programme a lancer ni dossier
    d'ecriture, sans empecher les reglages ordinaires ni ceux de l'utilisateur."""
    hostile = {"external_tools": [{"name": "projet", "command": "x"}], "log_dir": "ailleurs",
               "llm": {"cli": "programme-du-projet", "model": "modele-du-projet"}}
    with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as user:
        _write_json(os.path.join(project, ".claude", "supervisor.config.json"), hostile)
        _write_json(os.path.join(project, ".supervisor.json"), hostile)
        _write_json(os.path.join(user, "supervisor.config.json"),
                    {"external_tools": [{"name": "utilisateur", "command": "y"}]})
        with contextlib.redirect_stderr(io.StringIO()):     # l'avertissement attendu n'est pas du bruit utile ici
            cfg = load_config(project, user)
    problems = []
    if cfg["log_dir"]:
        problems.append("log_dir fixe par le projet")
    if cfg.llm.get("cli") != "claude":
        problems.append("llm.cli fixe par le projet")
    if [tool.get("name") for tool in cfg["external_tools"]] != ["utilisateur"]:
        problems.append("external_tools : le projet l'emporte sur l'utilisateur, ou celui de l'utilisateur est perdu")
    if cfg.llm.get("model") != "modele-du-projet":
        problems.append("reglage ordinaire du projet (llm.model) ignore a tort")
    return problems


def _encoding_problems() -> list:
    """La charge utile est lue en UTF-8 et la sortie du hook reste encodable sur un tube cp1252."""
    problems = []
    sent = json.dumps({"cwd": "dépôt →"}, ensure_ascii=False).encode("utf-8")
    saved = sys.stdin
    try:
        sys.stdin = io.TextIOWrapper(io.BytesIO(sent), encoding="cp1252", errors="replace")
        payload = _read_payload()
    finally:
        sys.stdin = saved
    if not payload or payload.get("cwd") != "dépôt →":
        problems.append("une charge utile UTF-8 accentuee est deformee a la lecture")
    encoded = _encode_hook_output({"reason": "problème → échec"})
    if not encoded.isascii() or json.loads(encoded)["reason"] != "problème → échec":
        problems.append("la sortie du hook n'est pas de l'ASCII pur ou perd des caracteres")
    return problems


def _quoting_problems() -> list:
    """Un nom de fichier du depot supervise ne doit jamais pouvoir ajouter une commande."""
    problems = []
    for name in ('a&b.py', 'a|b.py', 'a^b.py', 'a<b.py', 'a>b.py', 'x%PATH%.py', 'a!b.py', 'a"b.py', "a\nb.py"):
        if engine.quote_path(name, windows=True) is not None:
            problems.append("cmd.exe accepte %r" % name)
    if engine.quote_path("mon fichier.py", windows=True) != '"mon fichier.py"':
        problems.append("cmd.exe : un nom avec espace n'est pas entre guillemets doubles")
    if engine.quote_path("mon fichier.py", windows=False) != "'mon fichier.py'":
        problems.append("POSIX : un nom avec espace n'est pas protege")
    if engine.quote_path("a&b.py", windows=False) != "'a&b.py'":
        problems.append("POSIX : un nom avec & n'est pas protege")
    return problems


def self_test() -> int:
    fixtures = _fixtures_dir()
    if not fixtures:
        print("Dossier fixtures absent (cherche dans %s et son parent)." % HERE)
        return 1
    cfg = Config(json.loads(json.dumps(DEFAULTS)))
    rels = sorted(f for f in os.listdir(fixtures) if not f.startswith("."))
    files = load(fixtures, rels)
    findings = engine.analyze(fixtures, files, cfg)
    triggered = _print_findings_by_rule(files, findings)
    missing = sorted(EXPECTED_RULES - triggered)
    if missing:
        print("\nECHEC — regles attendues non declenchees : %s" % ", ".join(missing))
        return 1
    false_positives = sorted("%s:%d %s" % (f.file, f.line, f.rule) for f in findings
                             if f.file.startswith("clean_") and f.rule in FALSE_POSITIVE_RULES)
    if false_positives:
        print("\nECHEC — faux positifs sur les fixtures clean_* : %s" % ", ".join(false_positives))
        return 1
    for label, check in (("configuration de projet", _project_config_problems),
                         ("quoting des fichiers", _quoting_problems),
                         ("encodage", _encoding_problems)):
        problems = check()
        if problems:
            print("\nECHEC — %s : %s" % (label, ", ".join(problems)))
            return 1
    print("\nOK — toutes les regles attendues se declenchent.")
    return 0


def _use_utf8_output() -> None:
    """Sorties lisibles par Claude Code (UTF-8) meme quand elles sont redirigees : sous Windows,
    un tube utilise la page de codes (cp1252), ce qui deforme les accents et plante sur les autres
    caracteres. Une console interactive gere deja l'Unicode."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure") and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(args) -> int:
    _use_utf8_output()
    if "--self-test" in args:
        return self_test()
    if "--check" in args:
        return cli_main([a for a in args if a != "--check"])
    return hook_main()
