#!/usr/bin/env python3
"""Installe des skills du registre dans le dossier de skills de l'utilisateur, par copie.

Le depot reste la source de verite : la copie installee se verifie et se remplace, elle ne s'edite
pas. Aucun lien symbolique (ils demandent des privileges sous Windows).

Usage :
  python tools/install_skill.py install <nom> [<nom>...]    # copie, ou met a jour
  python tools/install_skill.py check <nom> [<nom>...]      # la copie correspond-elle au depot ?
  python tools/install_skill.py uninstall <nom> [<nom>...]
  python tools/install_skill.py --self-test

Options :
  --dest DIR   dossier de skills cible (defaut : ~/.claude/skills, ou $CLAUDE_CONFIG_DIR/skills)
  --root DIR   racine du registre (defaut : le depot qui contient ce script)

Une installation anterieure modifiee a la main n'est jamais ecrasee sans sauvegarde : elle est
copiee dans `<dest>/../skills-backup/<nom>-<horodatage>/` avant d'etre remplacee ou retiree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

MANIFEST = ".registry-install.json"
SKILL_FILE = "SKILL.md"
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def inside(base: str, *parts: str) -> str:
    """Chemin sous `base`, liens resolus ; refuse tout ce qui en sortirait."""
    base = os.path.realpath(base)
    path = os.path.realpath(os.path.join(base, *parts))
    if os.path.commonpath([base, path]) != base:
        raise SystemExit("chemin refuse, hors de %s : %s" % (base, os.path.join(*parts)))
    return path


def skill_name(value: str) -> str:
    if not NAME.match(value):
        raise SystemExit("nom de skill invalide : %r (kebab-case attendu)" % value)
    return value


def default_dest() -> str:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "skills")


def find_skill(root: str, name: str) -> str:
    """Dossier source du skill : skills/<categorie>/<nom>/, reconnu a son SKILL.md."""
    base = os.path.join(root, "skills")
    matches = [inside(base, category, name) for category in sorted(os.listdir(base))
               if os.path.isfile(inside(base, category, name, SKILL_FILE))]
    if len(matches) != 1:
        raise SystemExit("skill introuvable dans le registre : %s" % name)
    return matches[0]


def hashes(folder: str) -> dict:
    """{chemin relatif: sha256} des fichiers livres, hors caches et manifeste d'installation."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name == MANIFEST or name.endswith((".pyc", ".pyo")):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            found[os.path.relpath(path, folder).replace(os.sep, "/")] = digest
    return found


def read_manifest(folder: str):
    try:
        with open(inside(folder, MANIFEST), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def skill_version(folder: str) -> str:
    path = inside(folder, "metadata.yaml")
    if not os.path.isfile(path):
        return "?"
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip().strip("'\"")
    return "?"


def registry_commit(root: str):
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def remove_tree(path: str) -> None:
    def retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    shutil.rmtree(path, onerror=retry)


def copy_skill(source: str, target: str, files: dict) -> None:
    for rel in files:
        destination = inside(target, rel)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(inside(source, rel), destination)


def locally_modified(target: str, installed: dict) -> bool:
    """Vrai si la copie installee ne correspond plus a ce qui avait ete installe."""
    manifest = read_manifest(target)
    return manifest is None or manifest.get("files") != installed


def backup(dest: str, name: str, target: str) -> str:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = os.path.join(os.path.dirname(os.path.abspath(dest)), "skills-backup", "%s-%s" % (name, stamp))
    shutil.copytree(target, path)
    return path


def write_manifest(root: str, source: str, target: str, name: str, files: dict) -> None:
    data = {"name": name, "version": skill_version(source), "source": "ai-toolkit-registry",
            "commit": registry_commit(root), "files": files}
    with open(inside(target, MANIFEST), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def install(root: str, dest: str, name: str) -> str:
    source = find_skill(root, name)
    target = inside(dest, skill_name(name))
    wanted = hashes(source)
    note = ""
    if os.path.isdir(target):
        installed = hashes(target)
        if installed == wanted:
            write_manifest(root, source, target, name, wanted)
            return "%s : deja a jour (%s)" % (name, target)
        if locally_modified(target, installed):
            note = " ; ancienne copie modifiee sauvegardee dans %s" % backup(dest, name, target)
        remove_tree(target)
    copy_skill(source, target, wanted)
    write_manifest(root, source, target, name, wanted)
    return "%s : installe, version %s, %d fichiers (%s)%s" % (name, skill_version(source), len(wanted), target, note)


def check(root: str, dest: str, name: str):
    """Retourne (a_jour, message)."""
    source = find_skill(root, name)
    target = inside(dest, skill_name(name))
    if not os.path.isdir(target):
        return False, "%s : non installe dans %s" % (name, dest)
    wanted, installed = hashes(source), hashes(target)
    if wanted == installed:
        return True, "%s : identique au depot, version %s (%s)" % (name, skill_version(source), target)
    differing = sorted(p for p in set(wanted) | set(installed) if wanted.get(p) != installed.get(p))
    origin = "modifiee a la main depuis son installation" if locally_modified(target, installed) \
        else "en retard sur le depot"
    lines = ["%s : DIFFERENT du depot - copie %s" % (name, origin)]
    lines += ["  - %s (%s)" % (p, "absent du depot" if p not in wanted else
                              "absent de la copie" if p not in installed else "contenu different")
              for p in differing]
    return False, "\n".join(lines)


def uninstall(dest: str, name: str) -> str:
    target = inside(dest, skill_name(name))
    if not os.path.isdir(target):
        return "%s : non installe" % name
    note = ""
    if locally_modified(target, hashes(target)):
        note = " ; copie modifiee sauvegardee dans %s" % backup(dest, name, target)
    remove_tree(target)
    return "%s : retire de %s%s" % (name, dest, note)


def exits(action) -> bool:
    """Vrai si l'action se termine par un refus (SystemExit)."""
    try:
        action()
    except SystemExit:
        return True
    return False


def self_test() -> int:
    """Installe, modifie, reinstalle et retire un skill factice dans un dossier temporaire."""
    base = tempfile.mkdtemp(prefix="install-skill-selftest-")
    try:
        root, dest = os.path.join(base, "registry"), os.path.join(base, "home", "skills")
        skill = os.path.join(root, "skills", "development", "demo")
        os.makedirs(os.path.join(skill, "resources", "__pycache__"))
        for rel, text in ((SKILL_FILE, "---\nname: demo\n---\n"), ("metadata.yaml", "version: 1.2.3\n"),
                          ("resources/tool.py", "print('v1')\n"), ("resources/__pycache__/tool.pyc", "x")):
            with open(os.path.join(skill, rel), "w", encoding="utf-8") as fh:
                fh.write(text)
        failures = []

        def expect(label, condition):
            if not condition:
                failures.append(label)

        expect("non installe detecte", check(root, dest, "demo")[0] is False)
        for unsafe in ("../demo", "demo/..", "..", "Demo", ""):
            expect("nom dangereux refuse : %r" % unsafe, exits(lambda: uninstall(dest, unsafe)))
        install(root, dest, "demo")
        expect("copie identique apres installation", check(root, dest, "demo")[0])
        expect("caches non copies", not os.path.exists(os.path.join(dest, "demo", "resources", "__pycache__")))
        expect("reinstallation sans changement", "deja a jour" in install(root, dest, "demo"))
        with open(os.path.join(skill, "resources", "tool.py"), "w", encoding="utf-8") as fh:
            fh.write("print('v2')\n")
        ok, message = check(root, dest, "demo")
        expect("retard sur le depot detecte", not ok and "en retard" in message)
        expect("mise a jour sans sauvegarde inutile", "sauvegardee" not in install(root, dest, "demo"))
        with open(os.path.join(dest, "demo", SKILL_FILE), "a", encoding="utf-8") as fh:
            fh.write("retouche locale\n")
        ok, message = check(root, dest, "demo")
        expect("modification manuelle detectee", not ok and "modifiee a la main" in message)
        expect("copie modifiee sauvegardee avant remplacement", "sauvegardee" in install(root, dest, "demo"))
        saved = os.listdir(os.path.join(base, "home", "skills-backup"))
        with open(os.path.join(base, "home", "skills-backup", saved[0], SKILL_FILE), encoding="utf-8") as fh:
            expect("la sauvegarde contient la retouche", "retouche locale" in fh.read())
        expect("copie identique apres remplacement", check(root, dest, "demo")[0])
        uninstall(dest, "demo")
        expect("desinstallation", not os.path.exists(os.path.join(dest, "demo")))
        if failures:
            print("ECHEC - " + ", ".join(failures))
            return 1
        print("OK - installation, verification, sauvegarde et retrait se comportent comme attendu.")
        return 0
    finally:
        remove_tree(base)


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="Installe des skills du registre par copie.")
    parser.add_argument("action", nargs="?", choices=["install", "check", "uninstall"])
    parser.add_argument("names", nargs="*", help="noms de skills")
    parser.add_argument("--dest", default=None, help="dossier de skills cible")
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--self-test", action="store_true", help="verifie l'installateur")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.action or not args.names:
        parser.error("action et nom(s) de skill attendus")
    dest = os.path.abspath(args.dest or default_dest())
    root = os.path.abspath(args.root)
    code = 0
    for name in map(skill_name, args.names):
        if args.action == "install":
            print(install(root, dest, name))
        elif args.action == "uninstall":
            print(uninstall(dest, name))
        else:
            ok, message = check(root, dest, name)
            print(message)
            code = code or (0 if ok else 1)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
