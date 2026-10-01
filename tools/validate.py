#!/usr/bin/env python3
"""Validation du registre AI Toolkit Registry.

Verifie, pour chaque artefact et pour le depot dans son ensemble :
  - les metadonnees contre schemas/artifact.schema.json ;
  - la coherence entre `kind`, l'emplacement et la forme attendue (dossier ou fichier) ;
  - l'egalite entre `name` et le nom du dossier ou du fichier ;
  - la presence des fichiers obligatoires du type ;
  - l'egalite du front matter d'un SKILL.md et de son metadata.yaml ;
  - la coherence du manifeste de chaque plugin et de la marketplace ;
  - l'absence de chemin absolu local et de secret apparent ;
  - la synchronisation de INDEX.md.

Usage :
  python tools/validate.py              # depuis la racine du depot
  python tools/validate.py --root .     # racine explicite
  python tools/validate.py --json       # sortie machine
  python tools/validate.py --self-test  # verifie le validateur sur des cas construits

Dependances : PyYAML. Le reste est en bibliotheque standard ; jsonschema est utilise
s'il est disponible, sinon une validation reduite mais suffisante est appliquee.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML est requis : pip install pyyaml\n")
    raise SystemExit(2)

try:
    import jsonschema
except ImportError:
    jsonschema = None

# Type d'artefact -> (dossier, forme, fichiers obligatoires)
# forme "dir"  : un dossier par artefact, metadonnees dans metadata.yaml
# forme "file" : un fichier par artefact, metadonnees dans son front matter
KINDS = {
    "skill":        {"root": "skills",        "shape": "dir",  "required": ["SKILL.md", "metadata.yaml", "README.md"], "nested": True},
    "plugin":       {"root": "plugins",       "shape": "dir",  "required": [".claude-plugin/plugin.json", "metadata.yaml", "README.md"], "nested": False},
    "hook":         {"root": "hooks",         "shape": "dir",  "required": ["metadata.yaml", "README.md"], "nested": False},
    "instructions": {"root": "instructions",  "shape": "dir",  "required": ["metadata.yaml", "README.md"], "nested": False},
    "mcp-server":   {"root": "mcp",           "shape": "dir",  "required": ["metadata.yaml", "README.md"], "nested": False},
    "agent":        {"root": "agents",        "shape": "file", "required": [], "nested": False},
    "command":      {"root": "commands",      "shape": "file", "required": [], "nested": False},
    "output-style": {"root": "output-styles", "shape": "file", "required": [], "nested": False},
}
ROOT_TO_KIND = {v["root"]: k for k, v in KINDS.items()}

SURFACES = {"claude-code", "claude-desktop", "claude-ai", "claude-api"}
STATUSES = {"draft", "experimental", "stable", "deprecated"}
KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

ABSOLUTE_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]{1,2}(?:Users|workspace)|/home/|/Users/)"
    r"[\\/]?(?P<segment>[^\s\\/`'\"]*)")
# Un segment generique designe un emplacement, pas un poste de travail : la documentation a le
# droit de citer `C:\Users\<vous>\` ou `/home/<nom>/` pour expliquer une convention.
PLACEHOLDER_SEGMENT = re.compile(r"^(?:<[^>]*>|\.\.\.|\$|%|\{|$)")
SECRETS = [
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "cle AWS"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), "cle privee"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "jeton GitHub"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "jeton Slack"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"), "jeton JWT"),
]
SKIP_DIRS = {".git", ".idea", ".vscode", "__pycache__", "node_modules", ".claude"}
TEXT_EXT = {".md", ".yaml", ".yml", ".json", ".py", ".ps1", ".sh", ".txt", ".template", ".java", ".js", ".ts"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where: str, message: str):
        self.errors.append({"level": "error", "where": where, "message": message})

    def warn(self, where: str, message: str):
        self.warnings.append({"level": "warning", "where": where, "message": message})

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------- lecture

def read_front_matter(path: str):
    """Retourne (metadonnees, erreur). Front matter YAML delimite par --- en tete."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception as exc:
        return None, "lecture impossible (%s)" % exc
    if not text.startswith("---"):
        return None, "front matter YAML absent (le fichier doit commencer par ---)"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "front matter non termine (--- de fermeture manquant)"
    try:
        data = yaml.safe_load(text[3:end])
    except Exception as exc:
        return None, "front matter illisible (%s)" % exc
    if not isinstance(data, dict):
        return None, "front matter vide ou mal forme"
    return data, None


def read_yaml(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return None, "contenu vide ou mal forme"
        return data, None
    except Exception as exc:
        return None, "lecture impossible (%s)" % exc


# --------------------------------------------------------------------------- schema

def validate_schema(meta: dict, schema: dict, where: str, rep: Report) -> None:
    if jsonschema is not None:
        try:
            jsonschema.validate(meta, schema)
            return
        except jsonschema.ValidationError as exc:
            field = ".".join(str(p) for p in exc.absolute_path) or "(racine)"
            rep.error(where, "metadonnees invalides sur `%s` : %s" % (field, exc.message))
            return
    # Repli sans jsonschema : les controles qui comptent le plus.
    for field in schema.get("required", []):
        if field not in meta:
            rep.error(where, "champ obligatoire absent : `%s`" % field)
    unknown = set(meta) - set(schema.get("properties", {}))
    for field in sorted(unknown):
        rep.error(where, "champ inconnu : `%s`" % field)
    if "name" in meta and not KEBAB.match(str(meta["name"])):
        rep.error(where, "`name` n'est pas en kebab-case : %r" % meta["name"])
    if "version" in meta and not SEMVER.match(str(meta["version"])):
        rep.error(where, "`version` ne respecte pas SemVer : %r" % meta["version"])
    if "status" in meta and meta["status"] not in STATUSES:
        rep.error(where, "`status` invalide : %r" % meta["status"])
    if "kind" in meta and meta["kind"] not in KINDS:
        rep.error(where, "`kind` invalide : %r" % meta["kind"])
    for surface in meta.get("compatibility", []) or []:
        if surface not in SURFACES:
            rep.error(where, "surface inconnue dans `compatibility` : %r" % surface)


# --------------------------------------------------------------------------- artefacts

def discover(root: str):
    """Retourne la liste des artefacts : (kind, identifiant, chemin relatif, chemin des metadonnees)."""
    found = []
    for folder, spec in sorted(KINDS.items(), key=lambda kv: kv[1]["root"]):
        base = os.path.join(root, spec["root"])
        if not os.path.isdir(base):
            continue
        if spec["shape"] == "file":
            for name in sorted(os.listdir(base)):
                path = os.path.join(base, name)
                if not os.path.isfile(path) or name.startswith(".") or name == "README.md":
                    continue
                rel = os.path.relpath(path, root).replace("\\", "/")
                found.append((folder, os.path.splitext(name)[0], rel, rel))
            continue
        if spec["nested"]:
            for category in sorted(os.listdir(base)):
                cat_path = os.path.join(base, category)
                if not os.path.isdir(cat_path) or category in SKIP_DIRS:
                    continue
                for name in sorted(os.listdir(cat_path)):
                    art = os.path.join(cat_path, name)
                    if not os.path.isdir(art):
                        continue
                    rel = os.path.relpath(art, root).replace("\\", "/")
                    found.append((folder, name, rel, rel + "/metadata.yaml"))
        else:
            for name in sorted(os.listdir(base)):
                art = os.path.join(base, name)
                if not os.path.isdir(art) or name in SKIP_DIRS:
                    continue
                rel = os.path.relpath(art, root).replace("\\", "/")
                found.append((folder, name, rel, rel + "/metadata.yaml"))
    return found


def check_artifact(root: str, kind: str, ident: str, rel: str, meta_rel: str, schema: dict, rep: Report):
    spec = KINDS[kind]
    where = rel
    meta_path = os.path.join(root, meta_rel)

    if spec["shape"] == "file":
        meta, err = read_front_matter(meta_path)
    else:
        if not os.path.isfile(meta_path):
            rep.error(where, "metadata.yaml absent")
            return None
        meta, err = read_yaml(meta_path)
    if err:
        rep.error(where, err)
        return None

    validate_schema(meta, schema, where, rep)

    if meta.get("kind") != kind:
        rep.error(where, "`kind: %s` attendu d'apres l'emplacement, trouve %r"
                  % (kind, meta.get("kind")))
    if meta.get("name") != ident:
        rep.error(where, "`name: %r` ne correspond pas a %r (nom du %s)"
                  % (meta.get("name"), ident, "fichier" if spec["shape"] == "file" else "dossier"))

    for required in spec["required"]:
        if not os.path.exists(os.path.join(root, rel, required)):
            rep.error(where, "fichier obligatoire absent : %s" % required)

    if spec["nested"]:
        category = rel.split("/")[1]
        if meta.get("category") != category:
            rep.error(where, "`category: %r` ne correspond pas au dossier parent %r"
                      % (meta.get("category"), category))

    # Pour un skill, le SKILL.md EST l'artefact : son front matter doit etre identique au
    # metadata.yaml. Pour un autre type qui embarque un SKILL.md (un plugin, par exemple), ce
    # fichier est un composant distinct : sa description pilote le declenchement de la skill et
    # n'a pas a repeter celle de l'artefact. Seul le nom doit concorder.
    skill_md = os.path.join(root, rel, "SKILL.md")
    if spec["shape"] == "dir" and os.path.isfile(skill_md):
        fm, fm_err = read_front_matter(skill_md)
        if fm_err:
            rep.error(rel + "/SKILL.md", fm_err)
        elif kind == "skill":
            for field in ("kind", "name", "version", "description", "status", "compatibility"):
                if fm.get(field) != meta.get(field):
                    rep.error(rel + "/SKILL.md",
                              "`%s` differe entre SKILL.md (%r) et metadata.yaml (%r)"
                              % (field, fm.get(field), meta.get(field)))
        elif fm.get("name") != meta.get("name"):
            rep.error(rel + "/SKILL.md",
                      "`name: %r` ne correspond pas a l'artefact %r"
                      % (fm.get("name"), meta.get("name")))

    if kind == "plugin":
        check_plugin(root, rel, ident, meta, rep)

    if meta.get("status") == "draft":
        rep.warn(where, "statut `draft` : artefact non pret a etre utilise")
    return meta


def check_plugin(root: str, rel: str, ident: str, meta: dict, rep: Report):
    manifest_path = os.path.join(root, rel, ".claude-plugin", "plugin.json")
    if not os.path.isfile(manifest_path):
        return
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception as exc:
        rep.error(rel + "/.claude-plugin/plugin.json", "JSON invalide (%s)" % exc)
        return
    if manifest.get("name") != ident:
        rep.error(rel + "/.claude-plugin/plugin.json",
                  "`name: %r` ne correspond pas au dossier %r" % (manifest.get("name"), ident))
    if manifest.get("description", "").strip() == "":
        rep.warn(rel + "/.claude-plugin/plugin.json", "`description` absente")
    hooks_path = os.path.join(root, rel, "hooks", "hooks.json")
    if os.path.isfile(hooks_path):
        try:
            with open(hooks_path, "r", encoding="utf-8") as fh:
                hooks = json.load(fh)
        except Exception as exc:
            rep.error(rel + "/hooks/hooks.json", "JSON invalide (%s)" % exc)
            return
        blob = json.dumps(hooks)
        if "${CLAUDE_PLUGIN_ROOT}" not in blob:
            rep.warn(rel + "/hooks/hooks.json",
                     "aucune reference a ${CLAUDE_PLUGIN_ROOT} : les chemins sont-ils portables ?")
        for event, groups in (hooks.get("hooks") or {}).items():
            for group in groups:
                for handler in (group.get("hooks") or []):
                    if "command" not in handler and "args" not in handler:
                        rep.error(rel + "/hooks/hooks.json",
                                  "handler %s sans `command` ni `args`" % event)


def check_marketplace(root: str, plugins: list, rep: Report):
    path = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(path):
        if plugins:
            rep.error(".claude-plugin/marketplace.json",
                      "absent alors que le depot contient %d plugin(s)" % len(plugins))
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        rep.error(".claude-plugin/marketplace.json", "JSON invalide (%s)" % exc)
        return
    declared = {}
    for entry in data.get("plugins", []):
        source = entry.get("source")
        if isinstance(source, str):
            declared[entry.get("name")] = source
            target = os.path.normpath(os.path.join(root, source))
            if not os.path.isdir(target):
                rep.error(".claude-plugin/marketplace.json",
                          "`source` introuvable pour %r : %s" % (entry.get("name"), source))
            if ".." in source.split("/"):
                rep.error(".claude-plugin/marketplace.json",
                          "`source` remonte hors du depot pour %r" % entry.get("name"))
    for name in plugins:
        if name not in declared:
            rep.error(".claude-plugin/marketplace.json",
                      "plugin `%s` present dans plugins/ mais non declare" % name)
    for name in declared:
        if name not in plugins:
            rep.error(".claude-plugin/marketplace.json",
                      "plugin `%s` declare mais absent de plugins/" % name)


# --------------------------------------------------------------------------- depot

def check_hygiene(root: str, rep: Report):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if rel.startswith("tools/validate.py"):
                continue          # ce fichier contient les motifs de detection
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                for match in ABSOLUTE_PATH.finditer(line):
                    if PLACEHOLDER_SEGMENT.match(match.group("segment") or ""):
                        continue
                    rep.error("%s:%d" % (rel, idx),
                              "chemin absolu local (%s) : les conventions l'interdisent"
                              % match.group(0).strip())
                for rx, label in SECRETS:
                    if rx.search(line):
                        rep.error("%s:%d" % (rel, idx), "secret apparent (%s)" % label)
            if "\r\n" in text:
                rep.warn(rel, "fins de ligne CRLF alors que .editorconfig impose LF")


def check_index(root: str, artifacts: list, rep: Report):
    path = os.path.join(root, "INDEX.md")
    if not os.path.isfile(path):
        rep.error("INDEX.md", "absent : lancer `python tools/generate_index.py`")
        return
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    for kind, ident, rel, _ in artifacts:
        if rel not in text:
            rep.error("INDEX.md", "%s absent de l'index : relancer `python tools/generate_index.py`" % rel)


def check_surfaces_doc(root: str, artifacts: list, metas: dict, rep: Report):
    path = os.path.join(root, "docs", "surfaces.md")
    if not os.path.isfile(path):
        rep.warn("docs/surfaces.md", "absent")
        return
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    for kind, ident, rel, _ in artifacts:
        if ("`%s`" % ident) not in text:
            rep.warn("docs/surfaces.md",
                     "`%s` absent de la matrice des surfaces" % ident)


def validate(root: str) -> Report:
    rep = Report()
    schema_path = os.path.join(root, "schemas", "artifact.schema.json")
    if not os.path.isfile(schema_path):
        rep.error("schemas/artifact.schema.json", "absent")
        return rep
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    artifacts = discover(root)
    if not artifacts:
        rep.warn("(depot)", "aucun artefact trouve")
    metas = {}
    seen = {}
    for kind, ident, rel, meta_rel in artifacts:
        meta = check_artifact(root, kind, ident, rel, meta_rel, schema, rep)
        if meta:
            metas[rel] = meta
        if ident in seen:
            rep.error(rel, "identifiant deja utilise par %s" % seen[ident])
        else:
            seen[ident] = rel

    plugins = [ident for kind, ident, _, _ in artifacts if kind == "plugin"]
    check_marketplace(root, plugins, rep)
    check_hygiene(root, rep)
    check_index(root, artifacts, rep)
    check_surfaces_doc(root, artifacts, metas, rep)
    return rep, artifacts


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="Valide le registre.")
    parser.add_argument("--root", default=".", help="racine du depot (defaut : repertoire courant)")
    parser.add_argument("--json", action="store_true", help="sortie JSON")
    parser.add_argument("--strict", action="store_true", help="traite les avertissements comme des erreurs")
    parser.add_argument("--self-test", action="store_true", help="verifie le validateur")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    root = os.path.abspath(args.root)
    rep, artifacts = validate(root)
    if args.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings,
                          "artifacts": [{"kind": k, "name": n, "path": p} for k, n, p, _ in artifacts]},
                         ensure_ascii=False, indent=2))
    else:
        print("Registre : %s" % root)
        print("Artefacts : %d" % len(artifacts))
        for kind in sorted(KINDS):
            count = sum(1 for k, _, _, _ in artifacts if k == kind)
            if count:
                print("  %-14s %d" % (kind, count))
        print()
        for item in rep.errors:
            print("ERREUR  %s : %s" % (item["where"], item["message"]))
        for item in rep.warnings:
            print("ATTENTION  %s : %s" % (item["where"], item["message"]))
        if rep.ok and not rep.warnings:
            print("Aucun probleme.")
        elif rep.ok:
            print("\n%d avertissement(s), aucune erreur." % len(rep.warnings))
        else:
            print("\n%d erreur(s), %d avertissement(s)." % (len(rep.errors), len(rep.warnings)))
    if not rep.ok:
        return 1
    return 1 if (args.strict and rep.warnings) else 0


def self_test() -> int:
    """Construit un petit registre fautif en memoire disque et verifie la detection."""
    import shutil
    import tempfile
    base = tempfile.mkdtemp(prefix="registry-selftest-")
    try:
        os.makedirs(os.path.join(base, "schemas"))
        here = os.path.dirname(os.path.abspath(__file__))
        src_schema = os.path.join(os.path.dirname(here), "schemas", "artifact.schema.json")
        shutil.copy2(src_schema, os.path.join(base, "schemas", "artifact.schema.json"))
        # Un skill dont le name ne correspond pas au dossier, sans README.
        art = os.path.join(base, "skills", "development", "bon-nom")
        os.makedirs(art)
        with open(os.path.join(art, "metadata.yaml"), "w", encoding="utf-8") as fh:
            fh.write("kind: skill\nname: mauvais-nom\ndisplayName: X\ndescription: X\n"
                     "version: '1.0'\nstatus: stable\ncategory: testing\ntags: [a]\n"
                     "compatibility: [claude-code]\nauthors: [X]\nlicense: MIT\n")
        with open(os.path.join(art, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nkind: skill\nname: mauvais-nom\nversion: 2.0.0\n---\nTexte\n")
        rep, artifacts = validate(base)
        messages = " | ".join(i["message"] for i in rep.errors)
        expected = [
            ("name different du dossier", "ne correspond pas"),
            ("version non SemVer", "`version`"),
            ("category differente du dossier parent", "dossier parent"),
            ("README.md absent", "README.md"),
            ("front matter desynchronise", "differe entre SKILL.md"),
            ("INDEX.md absent", "generate_index"),
        ]
        missing = [label for label, needle in expected if needle not in messages]
        print("Constats : %d" % len(rep.errors))
        for item in rep.errors:
            print("  - %s : %s" % (item["where"], item["message"]))
        if missing:
            print("\nECHEC — controles attendus non declenches : %s" % ", ".join(missing))
            return 1
        print("\nOK — le validateur detecte les cas attendus.")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
