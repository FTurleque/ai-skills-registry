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
MARKER = "hooks/supervisor.py"


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


def copy_tree(dest: str) -> None:
    hooks_dest = os.path.join(dest, "hooks")
    pkg_dest = os.path.join(hooks_dest, "supervisor")
    os.makedirs(pkg_dest, exist_ok=True)
    shutil.copy2(os.path.join(HERE, "hooks", "supervisor.py"), hooks_dest)
    src_pkg = os.path.join(HERE, "hooks", "supervisor")
    for name in sorted(os.listdir(src_pkg)):
        if name.endswith(".py"):
            shutil.copy2(os.path.join(src_pkg, name), pkg_dest)
    agents_dest = os.path.join(dest, "agents")
    os.makedirs(agents_dest, exist_ok=True)
    shutil.copy2(os.path.join(HERE, "agents", "code-supervisor.md"), agents_dest)
    fixtures_dest = os.path.join(dest, "hooks", "fixtures")
    os.makedirs(fixtures_dest, exist_ok=True)
    for name in sorted(os.listdir(os.path.join(HERE, "fixtures"))):
        shutil.copy2(os.path.join(HERE, "fixtures", name), fixtures_dest)
    cfg_dest = os.path.join(dest, "supervisor.config.json")
    if not os.path.exists(cfg_dest):
        shutil.copy2(os.path.join(HERE, "supervisor.config.json"), cfg_dest)
        print("  configuration creee : %s" % cfg_dest)
    else:
        print("  configuration existante conservee : %s" % cfg_dest)


def load_settings(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print("  ATTENTION : %s illisible (%s). Rien n'a ete modifie." % (path, exc))
        raise SystemExit(2)


def save_settings(path: str, data: dict) -> None:
    if os.path.isfile(path):
        backup = path + ".bak"
        shutil.copy2(path, backup)
        print("  sauvegarde de l'ancien fichier : %s" % backup)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def hook_command(dest: str, py: str) -> str:
    script = os.path.join(dest, "hooks", "supervisor.py").replace("\\", "/")
    return '%s "%s"' % (py, script)


def merge_hooks(settings: dict, command: str) -> bool:
    changed = False
    hooks = settings.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        groups = hooks.setdefault(event, [])
        already = any(
            MARKER in str(h.get("command", ""))
            for g in groups if isinstance(g, dict)
            for h in (g.get("hooks") or []) if isinstance(h, dict)
        )
        if already:
            print("  hook %s deja present, mis a jour." % event)
            for g in groups:
                for h in (g.get("hooks") or []):
                    if MARKER in str(h.get("command", "")):
                        h["command"] = command
                        h["timeout"] = 300
            changed = True
            continue
        groups.append({"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": 300}]})
        print("  hook %s ajoute." % event)
        changed = True
    return changed


def remove_hooks(settings: dict) -> bool:
    changed = False
    hooks = settings.get("hooks") or {}
    for event in HOOK_EVENTS:
        groups = hooks.get(event) or []
        kept = []
        for g in groups:
            handlers = [h for h in (g.get("hooks") or []) if MARKER not in str(h.get("command", ""))]
            if handlers:
                g["hooks"] = handlers
                kept.append(g)
            else:
                changed = True
        if kept:
            hooks[event] = kept
        elif event in hooks:
            del hooks[event]
            changed = True
    if not hooks and "hooks" in settings:
        del settings["hooks"]
    return changed


def main(argv) -> int:
    dest = target_dir(argv)
    settings_path = os.path.join(dest, "settings.json")
    if "--uninstall" in argv:
        print("Desinstallation depuis %s" % dest)
        settings = load_settings(settings_path)
        if remove_hooks(settings):
            save_settings(settings_path, settings)
            print("  hooks retires de %s" % settings_path)
        for path in (os.path.join(dest, "hooks", "supervisor.py"),
                     os.path.join(dest, "hooks", "supervisor"),
                     os.path.join(dest, "hooks", "fixtures"),
                     os.path.join(dest, "agents", "code-supervisor.md")):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.isfile(path):
                os.remove(path)
        print("  fichiers supprimes. La configuration supervisor.config.json et les rapports sont conserves.")
        return 0

    py = python_command()
    print("Installation du superviseur de code")
    print("  cible        : %s" % dest)
    print("  interpreteur : %s" % py)
    os.makedirs(dest, exist_ok=True)
    copy_tree(dest)
    settings = load_settings(settings_path)
    if merge_hooks(settings, hook_command(dest, py)):
        save_settings(settings_path, settings)
        print("  settings.json ecrit : %s" % settings_path)

    print("\nVerification du moteur :")
    script = os.path.join(dest, "hooks", "supervisor.py")
    try:
        proc = subprocess.run([sys.executable, script, "--self-test"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        out = proc.stdout.decode("utf-8", "replace")
        print("\n".join("  " + l for l in out.strip().splitlines()[-4:]))
        if proc.returncode != 0:
            print("  ECHEC de l'auto-test : le superviseur est installe mais a verifier.")
    except Exception as exc:
        print("  auto-test impossible (%s)" % exc)

    print("""
Termine. Le superviseur se declenche a la fin de chaque reponse d'agent, dans tous les projets.

Pour l'utiliser a la main :
  %s "%s" --check            relecture des fichiers modifies
  %s "%s" --check --llm      idem, avec la relecture par modele
  @code-supervisor                                 depuis une session Claude Code

Reglages : %s
Rapports : <projet>/docs/rapport-supervisor/ (ignore par git, jamais commite)
""" % (py, script.replace("\\", "/"), py, script.replace("\\", "/"),
       os.path.join(dest, "supervisor.config.json")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
