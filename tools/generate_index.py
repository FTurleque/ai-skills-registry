#!/usr/bin/env python3
"""Genere INDEX.md : le catalogue de tous les artefacts du registre.

Usage :
  python tools/generate_index.py            # ecrit INDEX.md a la racine
  python tools/generate_index.py --check    # echoue si INDEX.md n'est pas a jour
  python tools/generate_index.py --root .   # racine explicite

Le fichier produit est entierement regenere : ne pas l'editer a la main.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from validate import KINDS, discover, read_front_matter, read_yaml  # noqa: E402

KIND_LABEL = {
    "skill": "Skills",
    "plugin": "Plugins",
    "agent": "Sous-agents",
    "command": "Commandes",
    "hook": "Hooks",
    "instructions": "Instructions de projet",
    "mcp-server": "Serveurs MCP",
    "output-style": "Styles de sortie",
}
KIND_ORDER = ["skill", "plugin", "agent", "command", "hook", "instructions", "mcp-server", "output-style"]
SURFACE_LABEL = {
    "claude-code": "Code",
    "claude-desktop": "Desktop",
    "claude-ai": "claude.ai",
    "claude-api": "API",
}
STATUS_BADGE = {
    "stable": "stable",
    "experimental": "experimental",
    "draft": "brouillon",
    "deprecated": "deprecie",
}


def load_meta(root: str, kind: str, rel: str, meta_rel: str):
    path = os.path.join(root, meta_rel)
    if KINDS[kind]["shape"] == "file":
        meta, err = read_front_matter(path)
    else:
        meta, err = read_yaml(path)
    return meta or {}


def build(root: str) -> str:
    artifacts = discover(root)
    by_kind = {}
    for kind, ident, rel, meta_rel in artifacts:
        by_kind.setdefault(kind, []).append((ident, rel, load_meta(root, kind, rel, meta_rel)))

    lines = [
        "# Index du registre",
        "",
        "Catalogue de tous les artefacts du depot, par type.",
        "",
        "> Fichier genere par `python tools/generate_index.py`. Ne pas l'editer a la main.",
        "",
        "## Resume",
        "",
        "| Type | Nombre |",
        "|------|-------:|",
    ]
    total = 0
    for kind in KIND_ORDER:
        count = len(by_kind.get(kind, []))
        total += count
        lines.append("| %s | %d |" % (KIND_LABEL[kind], count))
    lines += ["| **Total** | **%d** |" % total, ""]

    for kind in KIND_ORDER:
        items = by_kind.get(kind)
        if not items:
            continue
        lines += ["## %s" % KIND_LABEL[kind], "",
                  "| Artefact | Description | Version | Statut | Surfaces |",
                  "|----------|-------------|---------|--------|----------|"]
        for ident, rel, meta in sorted(items):
            surfaces = ", ".join(SURFACE_LABEL.get(s, s) for s in (meta.get("compatibility") or []))
            description = str(meta.get("description", "")).replace("|", "\\|").strip()
            if len(description) > 160:
                description = description[:157] + "..."
            lines.append("| [`%s`](%s) | %s | %s | %s | %s |" % (
                ident, rel, description, meta.get("version", "?"),
                STATUS_BADGE.get(meta.get("status"), meta.get("status", "?")), surfaces or "—"))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="Genere le catalogue des artefacts.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true",
                        help="ne rien ecrire ; sortir en erreur si INDEX.md differe")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    content = build(root)
    path = os.path.join(root, "INDEX.md")
    if args.check:
        current = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                current = fh.read()
        if current != content:
            print("INDEX.md n'est pas a jour : lancer `python tools/generate_index.py`")
            return 1
        print("INDEX.md est a jour.")
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("INDEX.md ecrit (%d artefact(s))." % len(discover(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
