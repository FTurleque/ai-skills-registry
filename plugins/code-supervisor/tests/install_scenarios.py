"""Scenarios de l'installeur : `install.py` lance dans un dossier de configuration jetable.

L'installeur ecrit dans le `settings.json` de l'utilisateur : il ne doit ni perdre ses reglages ni ses autres
hooks. Chaque scenario part d'un etat de depart (un `settings.json` ou rien), enchaine des appels
(installation, reinstallation, desinstallation) et releve le code de sortie, la sortie normalisee, le
`settings.json` obtenu, sa sauvegarde et la presence des fichiers installes. Reference :
`golden/install_scenarios.json`. La suite est ignoree si `install.py` n'est pas a cote du moteur teste."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

from hook_scenarios import Sandbox

OTHER_HOOK = {"type": "command", "command": "echo autre-hook", "timeout": 5}
OLD_OURS = {"type": "command", "command": 'python "/ancien/dossier/hooks/supervisor.py"', "timeout": 5}
# Fichiers dont on releve la presence : pas la liste complete, qui changerait a chaque module ajoute au moteur.
WATCHED = ("hooks/supervisor.py", "hooks/supervisor/runner.py", "hooks/fixtures", "agents/code-supervisor.md",
           "supervisor.config.json", "settings.json", "settings.json.bak")


def _scenarios() -> dict:
    """nom -> (settings.json de depart : None, texte ou objet JSON, appels successifs)."""
    return {
        "installation_neuve": (None, [[]]),
        "reglages_et_autres_hooks_conserves": (
            {"model": "opus", "hooks": {"Stop": [{"matcher": "", "hooks": [OTHER_HOOK]}],
                                        "PreToolUse": [{"matcher": "Bash", "hooks": [OTHER_HOOK]}]}}, [[]]),
        "reinstallation": (None, [[], []]),
        "ancien_hook_mis_a_jour": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": [OTHER_HOOK, OLD_OURS]}]}}, [[]]),
        "reglages_illisibles": ("{ pas du json", [[]]),
        "reglages_pas_un_objet": ("[1, 2]", [[]]),
        "groupe_qui_n_est_pas_un_objet": ({"hooks": {"Stop": ["texte", 3]}}, [[]]),
        "cle_hooks_pas_un_objet": ({"hooks": ["x"]}, [[]]),
        "evenement_pas_une_liste": ({"hooks": {"Stop": "x"}}, [[]]),
        "handler_qui_n_est_pas_un_objet": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": ["texte", OLD_OURS]}]}}, [[]]),
        "desinstallation_handler_qui_n_est_pas_un_objet": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": ["texte"]}]}}, [["--uninstall"]]),
        "desinstallation_groupe_vide_qui_n_est_pas_a_nous": (
            {"hooks": {"Stop": [{"matcher": "x", "hooks": []}, {"matcher": "", "hooks": [OTHER_HOOK, OLD_OURS]}]}},
            [["--uninstall"]]),
        "desinstallation_sans_nos_hooks": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": [OTHER_HOOK]}]}}, [["--uninstall"]]),
        "console_ascii": (None, [[]], {"env": {"PYTHONIOENCODING": "ascii"}}),
        "moteur_casse": (None, [[]], {"broken_engine": True}),
        "installation_de_projet": (None, [["--project", "{work}/projet"]]),
        "desinstallation_sans_rien": (None, [["--uninstall"]]),
        "desinstallation_apres_installation": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": [OTHER_HOOK]}]}}, [[], ["--uninstall"]]),
        "desinstallation_hooks_seuls": (None, [[], ["--uninstall"]]),
        "desinstallation_groupe_partage": (
            {"hooks": {"Stop": [{"matcher": "", "hooks": [OTHER_HOOK, OLD_OURS]}]}}, [["--uninstall"]]),
        "desinstallation_reglages_illisibles": ("{ pas du json", [["--uninstall"]]),
        "desinstallation_groupe_qui_n_est_pas_un_objet": ({"hooks": {"Stop": ["texte"]}}, [["--uninstall"]]),
    }


def _normalize_command(sandbox: Sandbox, value):
    """`python "<work>/.../supervisor.py"` : l'interpreteur depend de la machine."""
    value = sandbox.normalize(value)
    if isinstance(value, str):
        value = re.sub(r'^\S+ (?=")', "<python> ", value)
    return value


def _normalize_settings(sandbox: Sandbox, value):
    if isinstance(value, dict):
        return {key: (_normalize_command(sandbox, item) if key == "command" else _normalize_settings(sandbox, item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_settings(sandbox, item) for item in value]
    return value


def _normalize_output(sandbox: Sandbox, text: str) -> str:
    """Sortie lisible et stable : le detail de l'auto-test du moteur est reduit a sa conclusion."""
    text = sandbox.normalize(text)
    # Un traceback contient des chemins et des numeros de ligne du moteur teste : on ne garde que sa conclusion.
    text = re.sub(r"(?s)Traceback \(most recent call last\):.*\n(?=[^\n]*\Z)", "", text.strip())
    text = re.sub(r"(interpreteur : )\S+", r"\1<python>", text)
    text = re.sub(r'(?m)^(  )(?:python3?|\S*python\S*) (?=")', r"\1<python> ", text)
    kept, in_check = [], False
    for line in text.splitlines():
        if line.startswith("Verification du moteur"):
            in_check = True
        elif line.startswith("Termine."):
            in_check = False
        if not in_check or re.search(r"Verification|OK|ECHEC|impossible", line):
            kept.append(line)
    return "\n".join(kept)


def _read_json(path: str):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    try:
        return json.loads(text)
    except ValueError:
        return {"texte": text}


def _run_step(sandbox: Sandbox, installer: str, args: list, options: dict) -> dict:
    args = [arg.replace("{work}", sandbox.work) for arg in args]
    # Un dossier personnel jetable : si l'installeur ignorait CLAUDE_CONFIG_DIR, il viserait ce dossier-ci et
    # pas le `~/.claude` de la personne qui lance les tests (une desinstallation y effacerait son installation).
    home = os.path.join(sandbox.work, "home")
    os.makedirs(home, exist_ok=True)
    # Sortie en UTF-8 par defaut : la reference est la meme sous Windows (cp1252 sinon) et sous Linux.
    env = dict(sandbox.env, HOME=home, USERPROFILE=home, PYTHONIOENCODING="utf-8")
    env.update(options.get("env", {}))
    proc = subprocess.run([sys.executable, installer] + args, cwd=sandbox.work, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    output = proc.stdout.decode("utf-8", "replace")
    return {"exit": proc.returncode, "last_line": _normalize_output(sandbox, output.strip().splitlines()[-1]),
            "output": _normalize_output(sandbox, output)}


def _target_of(sandbox: Sandbox, args: list) -> str:
    if "--project" in args:
        return os.path.join(sandbox.work, "projet", ".claude")
    return sandbox.config_dir


def _with_broken_engine(sandbox: Sandbox, installer: str) -> str:
    """Copie des sources de l'installeur dont un module du moteur ne s'importe plus : l'auto-test doit echouer."""
    plugin = os.path.dirname(os.path.dirname(installer))
    copy = os.path.join(sandbox.work, "sources")
    for name in ("resources", "agents"):
        shutil.copytree(os.path.join(plugin, name), os.path.join(copy, name), ignore=shutil.ignore_patterns("__pycache__"))
    broken_module = os.path.join(copy, "resources", "supervisor", "rules_bugs.py")
    with open(broken_module, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("def casse(:\n")
    return os.path.join(copy, "resources", "install.py")


def _run_scenario(installer: str, initial, steps: list, options: dict) -> dict:
    sandbox = Sandbox(installer)
    try:
        target = sandbox.config_dir
        for args in steps:
            target = _target_of(sandbox, args) if "--project" in args else target
        os.makedirs(target, exist_ok=True)
        if "--project" in steps[0]:
            os.makedirs(os.path.join(sandbox.work, "projet"), exist_ok=True)
        if initial is not None:
            text = initial if isinstance(initial, str) else json.dumps(initial, indent=2)
            with open(os.path.join(target, "settings.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        if options.get("broken_engine"):
            installer = _with_broken_engine(sandbox, installer)
        results = [_run_step(sandbox, installer, args, options) for args in steps]
        return {
            "steps": results,
            "present": {rel: os.path.exists(os.path.join(target, rel)) for rel in WATCHED},
            "settings": _normalize_settings(sandbox, _read_json(os.path.join(target, "settings.json"))),
            "backup": _normalize_settings(sandbox, _read_json(os.path.join(target, "settings.json.bak"))),
        }
    finally:
        sandbox.close()


def run(script: str):
    """Reference des scenarios de l'installeur, ou None si `install.py` n'accompagne pas le moteur teste."""
    installer = os.path.join(os.path.dirname(os.path.abspath(script)), "install.py")
    if not os.path.isfile(installer):
        return None
    result = {}
    for name, (initial, steps, *extra) in _scenarios().items():
        result[name] = _run_scenario(installer, initial, steps, extra[0] if extra else {})
    return result
