#!/usr/bin/env python3
"""Inventaire et controles de coherence d'un corpus d'ADR.

Outil facultatif des skills adr-audit, adr-author et adr-check. Bibliotheque standard seule.
Il ne lit que des formes (emplacements, metadonnees, liens, index) : il ne juge ni la
pertinence d'une decision ni sa conformite dans le code.

    python adr_tool.py inventory [--root DIR] [--json]   # ou sont les ADR, quel statut declare
    python adr_tool.py check     [--root DIR] [--json]   # doublons, liens casses, index arc42

Codes de sortie : 0 rien a signaler, 1 au moins un constat, 2 erreur d'usage.
"""

import argparse
import json
import os
import re
import sys

SKIP_DIRS = {
    ".git", "node_modules", "target", "build", "dist", "out", "vendor", ".venv", "venv",
    "__pycache__", ".idea", ".gradle", ".mvn", ".next", "coverage",
}
ADR_DIRS = {
    "adr", "adrs", "decisions", "decision-records", "architecture-decisions",
    "architecture-decision-records", "architectural-decisions",
}
ADR_FILENAME = re.compile(r"^adr[-_ ]?\d", re.I)
NUMBERED = re.compile(r"^(\d{1,4})[-_ ]")
ARCHGATE_ID = re.compile(r"^([A-Z][A-Z0-9]*-\d{3,})[-_.]")

# Ordre significatif : le premier motif reconnu l'emporte.
STATUS_WORDS = [
    # "Supersedes ADR-2" ou "Remplace ADR-2" decrivent le remplacant, pas un document remplace.
    ("superseded", r"superseded|remplac[ée]e?s?\s+par\b|remplac[ée]e?s?\s*$|obsol[eè]te|caduqu"),
    ("deprecated", r"deprecat|d[ée]pr[ée]ci|abandonn|retir[ée]"),
    ("rejected", r"reject|rejet|refus"),
    ("accepted", r"accept|approved|approuv|valid[ée]|adopt"),
    ("proposed", r"propos|draft|brouillon|en discussion|pending|en attente|rfc"),
]
STATUS_HEADING = re.compile(r"^#{1,6}\s*(status|statut|[ée]tat)\s*$", re.I)
STATUS_COLUMN = re.compile(r"^\W*(status|statut|[ée]tat)\W*$", re.I)
STATUS_INLINE = re.compile(r"^\W*(?:status|statut|[ée]tat)[^\w:=]*[:=](.*)$", re.I)
STATUS_BOLD = re.compile(r"\*\*[ \t]*(?:status|statut)[ \t]*:([^*]+)\*\*", re.I)
FRONT_MATTER_PAIR = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:(.*)$")
TITLE_NUMBER = re.compile(r"^(?:adr[-_ ]?)?\d+[ \t]*[.:)-]", re.I)
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SECTION9_HEADING = re.compile(r"^#{1,6}[ \t]*0?9\b[.)]?[ \t]")
SECTION9_FILE = re.compile(r"(?:^|[-_/])0?9[-_]")
DECISION_WORD = re.compile(r"d[ée]cision|entscheidung", re.I)
STOP_WORDS = {
    "the", "a", "an", "of", "for", "to", "use", "using", "le", "la", "les", "de", "des", "du",
    "un", "une", "et", "en", "pour", "utiliser", "avec", "adr",
}


def posix(path):
    return path.replace(os.sep, "/")


def read_text(root, rel):
    """Lit un fichier du projet. Un chemin qui sort de la racine (lien symbolique, `..`) est refuse."""
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("chemin hors du projet : %s" % rel)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def is_not_an_adr(name):
    stem = os.path.splitext(name)[0].lower()
    return (stem in ("readme", "index") or stem.startswith(("template", "0000-", "0000_"))
            or stem.endswith(("-template", "_template", ".template")))


def has_section9_heading(text):
    return any(SECTION9_HEADING.match(line) and DECISION_WORD.search(line)
               for line in text.splitlines())


def walk_markdown(root):
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if name.lower().endswith(".md"):
                yield os.path.join(current, name)


def parse_front_matter(text):
    """Sous-ensemble de YAML suffisant pour un front matter d'ADR : scalaires et listes."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta, key = {}, None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, "
".join(lines[index + 1:])
        key = read_front_matter_line(meta, key, line)
    return {}, text


def read_front_matter_line(meta, key, line):
    """Range une ligne dans `meta` et retourne la cle courante (celle des elements de liste)."""
    stripped = line.strip()
    if key and line[:1] in (" ", "	") and stripped.startswith("- "):
        if not isinstance(meta.get(key), list):
            meta[key] = []
        meta[key].append(scalar(stripped[2:]))
        return key
    pair = FRONT_MATTER_PAIR.match(line)
    if not pair:
        return key
    key, raw = pair.group(1), pair.group(2).strip()
    if raw.startswith("[") and raw.endswith("]"):
        meta[key] = [scalar(part) for part in raw[1:-1].split(",") if part.strip()]
    else:
        meta[key] = scalar(raw) if raw else ""
    return key


def scalar(raw):
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def normalize_status(raw):
    if not raw:
        return "unknown"
    # Le premier mot de statut rencontre l'emporte : "Proposee, remplacerait X une fois acceptee"
    # est une proposition. A position egale, l'ordre de STATUS_WORDS departage.
    text = str(raw).lower()
    found = []
    for rank, (label, pattern) in enumerate(STATUS_WORDS):
        match = re.search(pattern, text, re.M)
        if match:
            found.append((match.start(), rank, label))
    return min(found)[2] if found else "unknown"


def status_under_heading(lines):
    for following in lines:
        if following.strip().startswith("#"):
            return ""
        if following.strip():
            return following.strip().strip("*_ ")
    return ""


def declared_status(meta, body):
    if meta.get("status"):
        return str(meta["status"])
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if STATUS_HEADING.match(line.strip()):
            found = status_under_heading(lines[index + 1:])
            if found:
                return found
        inline = STATUS_INLINE.match(line.strip())
        if inline and inline.group(1).strip():
            return inline.group(1).strip().strip("*_ .")
    # Statut porte par une phrase en gras, forme courante quand le schema n'a pas de champ.
    bold = STATUS_BOLD.search(body)
    return bold.group(1).strip() if bold else ""


def title_of(meta, body, fallback):
    if meta.get("title"):
        return str(meta["title"])
    for line in body.splitlines():
        if line.startswith("# "):
            return TITLE_NUMBER.sub("", line[2:].strip(), count=1).strip()
    return fallback


def format_of(meta):
    if {"id", "domain", "rules"} <= set(meta):
        return "archgate"
    return "front-matter" if meta else "markdown"


def identifier_of(meta, filename):
    if meta.get("id"):
        return str(meta["id"])
    stem = os.path.splitext(filename)[0]
    archgate = ARCHGATE_ID.match(filename)
    if archgate:
        return archgate.group(1)
    named = re.match(r"^adr[-_ ]?(\d+)", stem, re.I)
    if named:
        return "ADR-" + named.group(1)
    numbered = NUMBERED.match(stem)
    return numbered.group(1) if numbered else stem


def is_adr_candidate(root, path):
    rel = posix(os.path.relpath(path, root))
    name = os.path.basename(path)
    parent = os.path.basename(os.path.dirname(path)).lower()
    if is_not_an_adr(name):
        return False
    if "/.archgate/adrs/" in "/" + rel:
        return True
    if parent in ADR_DIRS:
        return True
    return bool(ADR_FILENAME.match(name))


def collect_adrs(root):
    adrs = []
    for path in walk_markdown(root):
        if not is_adr_candidate(root, path):
            continue
        rel = posix(os.path.relpath(path, root))
        meta, body = parse_front_matter(read_text(root, rel))
        name = os.path.basename(path)
        raw_status = declared_status(meta, body)
        rules_file = os.path.splitext(path)[0] + ".rules.ts"
        adrs.append({
            "path": rel,
            "registry": posix(os.path.dirname(rel)) or ".",
            "id": identifier_of(meta, name),
            "title": title_of(meta, body, os.path.splitext(name)[0]),
            "status_declared": raw_status,
            "status": normalize_status(raw_status),
            "format": format_of(meta),
            "rules": meta.get("rules") if isinstance(meta.get("rules"), bool) else None,
            "files": meta.get("files") if isinstance(meta.get("files"), list) else None,
            "rules_file": os.path.isfile(rules_file),
        })
    return adrs


def collect_arc42(root):
    """Fichiers du dossier arc42 et, parmi eux, ceux qui portent l'index des decisions."""
    documents, index = [], []
    for path in walk_markdown(root):
        rel = posix(os.path.relpath(path, root))
        if is_adr_candidate(root, path):
            continue
        # Un dossier arc42, pas un fichier qui en parle : seuls les noms de dossiers comptent.
        in_arc42 = any("arc42" in part.lower() for part in rel.split("/")[:-1])
        has_index = has_section9_heading(read_text(root, rel)) or (
            in_arc42 and bool(SECTION9_FILE.search(rel)) and bool(DECISION_WORD.search(rel)))
        if in_arc42 or has_index:
            documents.append(rel)
        if has_index:
            index.append(rel)
    return documents, index


def title_tokens(title):
    words = re.findall(r"[a-z0-9àâçéèêëîïôûùüÿœ]+", title.lower())
    return {word for word in words if word not in STOP_WORDS and len(word) > 2}


def broken_links(root, rel):
    findings = []
    base = os.path.dirname(os.path.join(root, rel))
    fenced = False
    for number, line in enumerate(read_text(root, rel).splitlines(), start=1):
        # Un lien dans un bloc de code ou entre accents graves est un exemple, pas une reference.
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for target in LINK.findall(re.sub(r"`[^`]*`", "", line)):
            if re.match(r"^([a-z][a-z0-9+.-]*:|#|//|<)", target, re.I):
                continue
            local = target.split("#", 1)[0].split("?", 1)[0]
            if local and not os.path.exists(os.path.normpath(os.path.join(base, local))):
                findings.append({
                    "kind": "lien-casse", "where": "%s:%d" % (rel, number),
                    "message": "lien vers `%s` : cible introuvable" % target,
                })
    return findings


def identity_findings(adrs):
    findings = []
    by_id = {}
    for adr in adrs:
        by_id.setdefault(adr["id"].lower(), []).append(adr)
    for same in by_id.values():
        if len(same) > 1:
            findings.append({
                "kind": "identifiant-en-double", "where": ", ".join(a["path"] for a in same),
                "message": "identifiant `%s` porte par %d documents" % (same[0]["id"], len(same)),
            })
    registries = sorted({adr["registry"] for adr in adrs})
    if len(registries) > 1:
        findings.append({
            "kind": "plusieurs-registres", "where": ", ".join(registries),
            "message": "ADR repartis dans %d emplacements : un seul doit etre editable"
                       % len(registries),
        })
    return findings + close_title_findings(adrs)


def titles_are_close(first, second):
    left, right = title_tokens(first["title"]), title_tokens(second["title"])
    return bool(left and right) and len(left & right) / float(len(left | right)) >= 0.5


def close_title_findings(adrs):
    pairs = [(first, second) for position, first in enumerate(adrs)
             for second in adrs[position + 1:]
             if first["id"].lower() != second["id"].lower() and titles_are_close(first, second)]
    return [{
        "kind": "doublon-possible",
        "where": "%s, %s" % (first["path"], second["path"]),
        "message": "titres proches (`%s` / `%s`) : a comparer a la lecture"
                   % (first["title"], second["title"]),
    } for first, second in pairs]


def metadata_findings(adrs):
    findings = []
    for adr in adrs:
        if adr["status"] == "unknown":
            findings.append({
                "kind": "statut-indetermine", "where": adr["path"],
                "message": "statut declare %s" % (
                    "illisible : `%s`" % adr["status_declared"] if adr["status_declared"]
                    else "absent"),
            })
        if adr["rules"] is True and not adr["rules_file"]:
            findings.append({
                "kind": "regle-declaree-sans-fichier", "where": adr["path"],
                "message": "`rules: true` sans fichier `.rules.ts` compagnon",
            })
        if adr["rules"] is False and adr["rules_file"]:
            findings.append({
                "kind": "fichier-de-regle-inactif", "where": adr["path"],
                "message": "fichier `.rules.ts` present mais `rules: false` : il n'est pas execute",
            })
    return findings


def table_cells(line):
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def indexed_statuses(text, pattern):
    """Statut lu dans la colonne Statut des lignes de tableau qui citent l'identifiant.

    Sans colonne Statut reconnaissable, rien n'est deduit : un titre ou un lien peut contenir
    un mot de statut sans en etre un.
    """
    statuses, column = [], None
    for line in text.splitlines():
        cells = table_cells(line)
        if cells is None:
            column = None
            continue
        header = [i for i, cell in enumerate(cells) if STATUS_COLUMN.match(cell)]
        if header:
            column = header[0]
        elif column is not None and column < len(cells):
            # L'identifiant doit etre cite hors de la cellule Statut : "remplacerait X" dans le
            # statut d'une autre decision ne fait pas de la ligne celle de X.
            others = cells[:column] + cells[column + 1:]
            if any(re.search(pattern, cell) for cell in others):
                statuses.append(normalize_status(cells[column]))
    return statuses


def index_findings(root, index_files, adrs):
    findings = []
    for rel in index_files:
        text = read_text(root, rel)
        for adr in adrs:
            findings.extend(index_entry_findings(rel, text, adr))
    return findings


def index_entry_findings(rel, text, adr):
    pattern = r"(?<![\w-])%s(?![\w-])" % re.escape(adr["id"])
    if not re.search(pattern, text) and os.path.basename(adr["path"]) not in text:
        return [{
            "kind": "adr-absent-de-l-index", "where": rel,
            "message": "`%s` (%s) n'apparait pas dans l'index des decisions"
                       % (adr["id"], adr["path"]),
        }]
    return [{
        "kind": "statut-divergent", "where": rel,
        "message": "`%s` : index `%s`, ADR `%s`" % (adr["id"], indexed, adr["status"]),
    } for indexed in indexed_statuses(text, pattern)
        if "unknown" not in (indexed, adr["status"]) and indexed != adr["status"]]


def run_inventory(root):
    adrs = collect_adrs(root)
    documents, index_files = collect_arc42(root)
    return {"adrs": adrs, "arc42": documents, "index": index_files}


def run_check(root):
    result = run_inventory(root)
    adrs = result["adrs"]
    findings = identity_findings(adrs) + metadata_findings(adrs)
    for rel in sorted(set(result["arc42"]) | {adr["path"] for adr in adrs}):
        findings.extend(broken_links(root, rel))
    findings.extend(index_findings(root, result["index"], adrs))
    result["findings"] = findings
    return result


def print_inventory(result):
    adrs = result["adrs"]
    if not adrs:
        print("Aucun ADR trouve.")
    for adr in adrs:
        rules = {True: "regles", False: "sans regle", None: "-"}[adr["rules"]]
        print("%-10s %-11s %-12s %-11s %s  [%s]" % (
            adr["id"], adr["status"], adr["format"], rules, adr["path"], adr["title"]))
    print("\nDossier arc42 : %s" % (", ".join(result["arc42"]) or "non trouve"))
    print("Index des decisions : %s" % (", ".join(result["index"]) or "non trouve"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["inventory", "check"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    # Un titre d'ADR peut porter un caractere que la console Windows (cp1252) ne sait pas ecrire.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("Dossier introuvable : %s" % args.root, file=sys.stderr)
        return 2

    result = run_inventory(root) if args.command == "inventory" else run_check(root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "inventory":
        print_inventory(result)
    else:
        for finding in result["findings"]:
            print("[%s] %s : %s" % (finding["kind"], finding["where"], finding["message"]))
        print("%d ADR, %d constat(s). Controle de forme uniquement." % (
            len(result["adrs"]), len(result["findings"])))
    if args.command == "check" and result["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
