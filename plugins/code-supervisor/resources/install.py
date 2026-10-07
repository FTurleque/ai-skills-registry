#!/usr/bin/env python3
"""Installe le superviseur de code dans la configuration utilisateur de Claude Code.

  python install.py                 # installation globale (~/.claude)
  python install.py --project .     # installation limitee a un projet (<projet>/.claude)
  python install.py --uninstall     # retire les hooks et les fichiers installes
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_EVENTS = ("Stop", "SubagentStop")
HOOK_TIMEOUT_SECONDS = 300
SELF_TEST_TIMEOUT_SECONDS = 180
SELF_TEST_TAIL_LINES = 4
MARKER = "hooks/supervisor.py"


def say(text: str = "") -> None:
    """Toute la sortie de l'installeur passe ici : c'est son produit, pas une trace de mise au point."""
    sys.stdout.write(text + "\n")


def target_dir(argv) -> str:
    if "--project" in argv:
        i = argv.index("--project")
        root = argv[i + 1] if len(argv) > i + 1 else "."
        return os.path.join(os.path.abspath(root), ".claude")
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def python_command() -> str:
    for candidate in ("python3", "python"):
        path = shutil.which(candidate)
        if path:
            # Sur Windows, python.exe est plus courant ; on garde le nom court,
            # resolu via le PATH au moment du declenchement du hook.
            return candidate
    return sys.executable or "python"


def _copy_files(src_dir: str, dest_dir: str, only_py: bool = False) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        if not only_py or name.endswith(".py"):
            shutil.copy2(os.path.join(src_dir, name), dest_dir)


def copy_tree(dest: str) -> None:
    hooks_dest = os.path.join(dest, "hooks")
    os.makedirs(hooks_dest, exist_ok=True)
    shutil.copy2(os.path.join(HERE, "supervisor.py"), hooks_dest)
    _copy_files(os.path.join(HERE, "supervisor"), os.path.join(hooks_dest, "supervisor"), only_py=True)
    agents_dest = os.path.join(dest, "agents")
    os.makedirs(agents_dest, exist_ok=True)
    shutil.copy2(os.path.join(HERE, "..", "agents", "code-supervisor.md"), agents_dest)
    _copy_files(os.path.join(HERE, "fixtures"), os.path.join(hooks_dest, "fixtures"))
    config_dest = os.path.join(dest, "supervisor.config.json")
    if not os.path.exists(config_dest):
        shutil.copy2(os.path.join(HERE, "supervisor.config.json"), config_dest)
        say("  configuration creee : %s" % config_dest)
    else:
        say("  configuration existante conservee : %s" % config_dest)


def _refuse_settings(path: str, reason) -> None:
    say("  ATTENTION : %s illisible (%s). Rien n'a ete modifie." % (path, reason))
    raise SystemExit(2)


def _settings_problem(settings) -> str:
    """Ce qui empeche d'ajouter ou de retirer nos hooks dans ce contenu, ou "" s'il convient."""
    if not isinstance(settings, dict):
        return "ce n'est pas un objet JSON"
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return "la cle hooks n'est pas un objet"
    if any(not isinstance(hooks.get(event, []), list) for event in HOOK_EVENTS):
        return "un evenement de hooks n'est pas une liste"
    return ""


def load_settings(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            settings = json.load(fh)
    except (OSError, ValueError) as exc:
        _refuse_settings(path, exc)
    problem = _settings_problem(settings)
    if problem:
        _refuse_settings(path, problem)
    return settings


def save_settings(path: str, settings: dict) -> None:
    if os.path.isfile(path):
        backup = path + ".bak"
        shutil.copy2(path, backup)
        say("  sauvegarde de l'ancien fichier : %s" % backup)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def hook_command(dest: str, python: str) -> str:
    script = os.path.join(dest, "hooks", "supervisor.py").replace("\\", "/")
    return '%s "%s"' % (python, script)


def _is_ours(handler) -> bool:
    return isinstance(handler, dict) and MARKER in str(handler.get("command", ""))


def _handlers(groups) -> list:
    return [h for g in groups if isinstance(g, dict) for h in (g.get("hooks") or []) if isinstance(h, dict)]


def _refresh_handlers(groups, command: str) -> None:
    for group in (g for g in groups if isinstance(g, dict)):
        for handler in (h for h in (group.get("hooks") or []) if _is_ours(h)):
            handler["command"] = command
            handler["timeout"] = HOOK_TIMEOUT_SECONDS


def _merge_event(hooks: dict, event: str, command: str) -> None:
    groups = hooks.setdefault(event, [])
    if any(_is_ours(handler) for handler in _handlers(groups)):
        say("  hook %s deja present, mis a jour." % event)
        _refresh_handlers(groups, command)
        return
    groups.append({"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": HOOK_TIMEOUT_SECONDS}]})
    say("  hook %s ajoute." % event)


def merge_hooks(settings: dict, command: str) -> None:
    hooks = settings.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        _merge_event(hooks, event, command)


def _strip_group(group):
    """(groupe a conserver ou None, vrai si un de nos handlers en a ete retire). Ce qui n'est pas a nous reste."""
    if not isinstance(group, dict):
        return group, False
    handlers = group.get("hooks") or []
    remaining = [h for h in handlers if not _is_ours(h)]
    if len(remaining) == len(handlers):
        return group, False
    if not remaining:
        return None, True
    group["hooks"] = remaining
    return group, True


def _strip_event(hooks: dict, event: str) -> bool:
    """Retire nos handlers de l'evenement ; vrai si le contenu de `hooks` a change."""
    kept, changed = [], False
    for group in hooks.get(event) or []:
        group, touched = _strip_group(group)
        changed = changed or touched
        if group is not None:
            kept.append(group)
    if kept:
        hooks[event] = kept
    elif event in hooks:
        del hooks[event]
        changed = True
    return changed


def remove_hooks(settings: dict) -> bool:
    hooks = settings.get("hooks") or {}
    changed = False
    for event in HOOK_EVENTS:
        changed = _strip_event(hooks, event) or changed
    if not hooks and "hooks" in settings:
        del settings["hooks"]
    return changed


def _installed_paths(dest: str) -> tuple:
    return (os.path.join(dest, "hooks", "supervisor.py"),
            os.path.join(dest, "hooks", "supervisor"),
            os.path.join(dest, "hooks", "fixtures"),
            os.path.join(dest, "agents", "code-supervisor.md"))


def _remove_path(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.isfile(path):
        os.remove(path)


def uninstall(dest: str) -> int:
    settings_path = os.path.join(dest, "settings.json")
    say("Desinstallation depuis %s" % dest)
    settings = load_settings(settings_path)
    if remove_hooks(settings):
        save_settings(settings_path, settings)
        say("  hooks retires de %s" % settings_path)
    for path in _installed_paths(dest):
        _remove_path(path)
    say("  fichiers supprimes. La configuration supervisor.config.json et les rapports sont conserves.")
    return 0


def _self_test_report(script: str) -> tuple:
    """(code de retour, fin de la sortie de l'auto-test du moteur installe)."""
    command = [sys.executable, script, "--self-test"]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=SELF_TEST_TIMEOUT_SECONDS)
    out = proc.stdout.decode("utf-8", "replace")
    tail = out.strip().splitlines()[-SELF_TEST_TAIL_LINES:]
    indented = ["  " + line for line in tail]
    return proc.returncode, "\n".join(indented)


def _run_self_test(script: str) -> None:
    say("\nVerification du moteur :")
    try:
        code, report = _self_test_report(script)
    except Exception as exc:
        say("  auto-test impossible (%s)" % exc)
        return
    say(report)
    if code != 0:
        say("  ECHEC de l'auto-test : le superviseur est installe mais a verifier.")


USAGE = """
Termine. Le superviseur se declenche a la fin de chaque reponse d'agent, dans tous les projets.

Pour l'utiliser a la main :
  %(python)s "%(script)s" --check            relecture des fichiers modifies
  %(python)s "%(script)s" --check --llm      idem, avec la relecture par modele
  @code-supervisor                                 depuis une session Claude Code

Reglages : %(config)s
Rapports : <projet>/docs/rapport-supervisor/ (ignore par git, jamais commite)
"""


def install(dest: str) -> int:
    settings_path = os.path.join(dest, "settings.json")
    python = python_command()
    say("Installation du superviseur de code")
    say("  cible        : %s" % dest)
    say("  interpreteur : %s" % python)
    settings = load_settings(settings_path)     # avant toute copie : s'il est refuse, rien n'est modifie
    os.makedirs(dest, exist_ok=True)
    copy_tree(dest)
    merge_hooks(settings, hook_command(dest, python))
    save_settings(settings_path, settings)
    say("  settings.json ecrit : %s" % settings_path)
    script = os.path.join(dest, "hooks", "supervisor.py")
    _run_self_test(script)
    say(USAGE % {"python": python, "script": script.replace("\\", "/"),
                 "config": os.path.join(dest, "supervisor.config.json")})
    return 0


def main(argv) -> int:
    # Une console qui ne sait pas afficher un caractere (cp1252, ASCII) montre « ? » au lieu de faire echouer l'installation.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    dest = target_dir(argv)
    return uninstall(dest) if "--uninstall" in argv else install(dest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
