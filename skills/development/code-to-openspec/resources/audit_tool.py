#!/usr/bin/env python3
"""Controles deterministes pour le skill code-to-openspec.

Sous-commandes :
  check    valide les constats (findings/*.md) et leur tracabilite vers les changements OpenSpec
  snapshot enregistre l'empreinte des fichiers-preuves des constats
  drift    compare les fichiers-preuves aux empreintes enregistrees
  next-id  affiche le prochain identifiant de constat libre

Prerequis : Python 3.8+, bibliotheque standard seulement. Git n'est pas necessaire.
Facultatif : le skill fonctionne sans ce script (les memes controles se font a la main).
Codes de sortie : 0 = rien a signaler, 1 = erreur ou derive detectee, 2 = usage.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

VOCABULARY = {
    "qualification": {"confirmed-defect", "potential-risk", "proposed-improvement", "decision-to-clarify"},
    "status": {"open", "in-change", "resolved", "rejected", "stale"},
    "priority": {"P0", "P1", "P2", "P3"},
    "evidence_level": {"executed", "traced", "local-read", "documentary"},
    "expected_status": {"documented", "proposed", "unknown"},
    "cause_status": {"demonstrated", "hypothesis", "unknown"},
}
REQUIRED_FIELDS = ("id", "title", "qualification", "status", "priority", "priority_rationale",
                   "evidence_level", "evidence", "current_behavior", "expected_status")
FIELDS_UNLESS_DECISION = ("minimal_fix", "acceptance")
FINDING_ID_PATTERN = re.compile(r"^F-\d{3,}$")
SNAPSHOT_NAME = "evidence-snapshot.json"
GATE_MESSAGE = "attendu non documente : validated_by (decision de l'utilisateur ou D-NNN) est exige avant le statut %s"
BOM = "﻿"
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
LIST_ITEM = re.compile(r"^\s*-\s+")
EVIDENCE_REFERENCE = re.compile(r"^(?P<path>.+?)(?::(?P<lines>\d+(?:-\d+)?))?$")


# --- lecture du front matter (sous-ensemble de YAML, une valeur par ligne) -------------------

def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_inline_list(body):
    items = re.findall(r'"[^"]*"|\'[^\']*\'|[^,]+', body)
    return [_unquote(item) for item in items if item.strip()]


def _front_matter_bounds(text):
    """Retourne (lignes, indice de fermeture, erreur)."""
    lines = text.lstrip(BOM).splitlines()
    if not lines or lines[0].strip() != "---":
        return lines, 0, "front matter absent (le fichier doit commencer par ---)"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines, index, None
    return lines, 0, "front matter non termine (--- de fermeture manquant)"


def _read_block_list(lines, start, end):
    """Lit les lignes `- element` qui suivent une cle vide. Retourne (elements, indice suivant)."""
    items, index = [], start
    while index < end and (LIST_ITEM.match(lines[index]) or not lines[index].strip()):
        if lines[index].strip():
            items.append(_unquote(LIST_ITEM.sub("", lines[index], count=1)))
        index += 1
    return items, index


def _parse_value(key, raw, lines, next_index, end):
    """Retourne (valeur, indice suivant, erreur)."""
    if raw == "":
        items, next_index = _read_block_list(lines, next_index, end)
        return (items if items else ""), next_index, None
    if raw.startswith("["):
        if not raw.endswith("]"):
            return None, next_index, "liste en ligne non terminee pour `%s`" % key
        return _split_inline_list(raw[1:-1]), next_index, None
    return _unquote(raw), next_index, None


def parse_front_matter(text):
    """Retourne (dict, erreur). Valeurs : str ou list[str]."""
    lines, end, error = _front_matter_bounds(text)
    if error:
        return None, error
    fields, index = {}, 1
    while index < end:
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key_match = KEY_LINE.match(line)
        if not key_match:
            return None, "ligne de front matter illisible : %r" % line
        key = key_match.group(1)
        value, index, error = _parse_value(key, key_match.group(2).strip(), lines, index, end)
        if error:
            return None, error
        fields[key] = value
    return fields, None


def as_list(value):
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


# --- constats ---------------------------------------------------------------------------------

class Finding:
    def __init__(self, path, fields, error):
        self.path, self.fields, self.error = path, fields or {}, error

    @property
    def fid(self):
        return str(self.fields.get("id", "")).strip()

    def get(self, key):
        return self.fields.get(key, "")

    def evidence_entries(self):
        return as_list(self.get("evidence"))

    def evidence_files(self):
        """Liste de (chemin, lignes|None) pour les preuves de type fichier."""
        files = []
        for entry in self.evidence_entries():
            if entry.lower().startswith("run:"):
                continue
            reference = EVIDENCE_REFERENCE.match(entry.strip())
            files.append((reference.group("path"), reference.group("lines")))
        return files

    def has_run_evidence(self):
        return any(entry.lower().startswith("run:") for entry in self.evidence_entries())


def load_findings(audit_dir):
    folder = audit_dir / "findings"
    if not folder.is_dir():
        return None
    findings = []
    for path in sorted(folder.glob("*.md")):
        fields, error = parse_front_matter(path.read_text(encoding="utf-8"))
        findings.append(Finding(path, fields, error))
    return findings


def findings_or_report(audit_dir):
    """Retourne les constats, ou None apres avoir signale l'absence du dossier findings/."""
    findings = load_findings(audit_dir)
    if findings is None:
        say("Aucun dossier findings/ dans %s" % audit_dir)
    return findings


def is_unsafe_path(path):
    return bool(re.match(r"^([A-Za-z]:[\\/]|[\\/]|~)", path)) or ".." in re.split(r"[\\/]", path)


def normalize(text):
    return re.sub(r"\s+", " ", text.strip()).casefold()


# --- tracabilite OpenSpec -------------------------------------------------------------------

def find_change_dir(name, openspec_root, audit_dir):
    candidates = [openspec_root / "changes" / name]
    archive = openspec_root / "changes" / "archive"
    if archive.is_dir():
        candidates += sorted(archive.glob("*-%s" % name))
    candidates.append(audit_dir / "changes-draft" / name)
    return next((candidate for candidate in candidates if candidate.is_dir()), None)


def read_headings(change_dir, pattern):
    specs_dir = change_dir / "specs"
    if not specs_dir.is_dir():
        return set()
    headings = set()
    for spec in specs_dir.rglob("*.md"):
        for line in spec.read_text(encoding="utf-8").splitlines():
            heading = re.match(pattern, line)
            if heading:
                headings.add(normalize(heading.group(1)))
    return headings


def skips_specs(change_dir):
    meta = change_dir / ".openspec.yaml"
    return meta.is_file() and re.search(r"^skip_specs:\s*true\b", meta.read_text(encoding="utf-8"), re.M)


def mentions(path, finding_id):
    return path.is_file() and re.search(r"\b%s\b" % re.escape(finding_id), path.read_text(encoding="utf-8")) is not None


# --- check ---------------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where, msg):
        self.errors.append("ERREUR %s : %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("ATTENTION %s : %s" % (where, msg))


def check_required(finding, label, report):
    missing = [key for key in REQUIRED_FIELDS if not as_list(finding.get(key))]
    if finding.get("qualification") != "decision-to-clarify":
        missing += [key for key in FIELDS_UNLESS_DECISION if not as_list(finding.get(key))]
    for key in missing:
        report.error(label, "champ obligatoire absent ou vide : %s" % key)


def check_vocabulary(finding, label, report):
    for key, allowed in VOCABULARY.items():
        value = finding.get(key)
        if value and value not in allowed:
            report.error(label, "`%s` = %r hors vocabulaire (%s)" % (key, value, ", ".join(sorted(allowed))))


def check_identity(finding, label, report):
    if not finding.fid:
        return
    if not FINDING_ID_PATTERN.match(finding.fid):
        report.error(label, "identifiant %r invalide (attendu F-NNN)" % finding.fid)
    elif not finding.path.name.startswith(finding.fid):
        report.error(label, "le nom de fichier doit commencer par l'identifiant (%s-...)" % finding.fid)


def check_fields(finding, report):
    label = finding.fid or finding.path.name
    check_required(finding, label, report)
    check_vocabulary(finding, label, report)
    check_identity(finding, label, report)


def check_evidence_files(finding, root, report):
    for path, _lines in finding.evidence_files():
        if is_unsafe_path(path):
            report.error(finding.fid, "preuve avec chemin absolu ou hors du projet : %s" % path)
        elif not (root / path).exists() and finding.get("status") not in ("resolved", "rejected", "stale"):
            report.warn(finding.fid, "fichier-preuve introuvable : %s" % path)


def check_confirmed_defect(finding, report):
    label, level = finding.fid, finding.get("evidence_level")
    if level not in ("executed", "traced"):
        report.error(label, "un defaut confirme exige evidence_level executed ou traced (obtenu : %s)"
                     % (level or "vide"))
    expected = finding.get("expected_status")
    if expected == "unknown":
        report.error(label, "un defaut confirme exige un attendu (expected_status unknown)")
    if expected == "documented" and not finding.get("expected_source"):
        report.error(label, "expected_status documented sans expected_source")
    if expected == "proposed":
        report.warn(label, "defaut confirme face a une exigence seulement proposee : justifier (invariant evident ?)")
    if finding.get("priority") in ("P0", "P1") and not (finding.has_run_evidence() or finding.get("reproduction")):
        report.warn(label, "defaut %s sans reproduction (`run:` ou champ reproduction)" % finding.get("priority"))


def check_evidence(finding, root, report):
    check_evidence_files(finding, root, report)
    if finding.get("evidence_level") == "executed" and not finding.has_run_evidence():
        report.error(finding.fid, "evidence_level `executed` sans entree `run: commande -> resultat`")
    if finding.get("qualification") == "confirmed-defect":
        check_confirmed_defect(finding, report)


def check_dependencies(finding, known_ids, report):
    for dependency in as_list(finding.get("depends_on")):
        if dependency not in known_ids:
            report.error(finding.fid, "depends_on reference un constat inconnu : %s" % dependency)


def check_validation_gate(finding, report):
    """Une exigence non documentee ne passe pas en changement sans validation de l'utilisateur."""
    if finding.get("expected_status") == "documented" or finding.get("validated_by"):
        return
    message = GATE_MESSAGE % finding.get("status")
    report.error(finding.fid, message)


def check_change_trace(finding, change_dir, report):
    label, name = finding.fid, finding.get("change")
    if not mentions(change_dir / "tasks.md", label):
        report.error(label, "tasks.md du changement %s ne cite pas %s" % (name, label))
    if not mentions(change_dir / "proposal.md", label):
        report.warn(label, "proposal.md du changement %s ne cite pas %s" % (name, label))
    wanted_requirements = as_list(finding.get("requirements"))
    if not wanted_requirements and not skips_specs(change_dir):
        report.warn(label, "aucune exigence reliee (requirements) alors que le changement n'est pas skip_specs")
    known_requirements = read_headings(change_dir, r"^###\s+Requirement:\s*(.+?)\s*$")
    known_scenarios = read_headings(change_dir, r"^####\s+Scenario:\s*(.+?)\s*$")
    for requirement in wanted_requirements:
        if normalize(requirement) not in known_requirements:
            report.error(label, "exigence introuvable dans les deltas de %s : %s" % (name, requirement))
    for scenario in as_list(finding.get("scenarios")):
        if normalize(scenario) not in known_scenarios:
            report.error(label, "scenario introuvable dans les deltas de %s : %s" % (name, scenario))


def check_links(finding, known_ids, openspec_root, audit_dir, report):
    check_dependencies(finding, known_ids, report)
    if finding.get("status") not in ("in-change", "resolved"):
        return
    check_validation_gate(finding, report)
    name = finding.get("change")
    if not name and finding.get("status") == "resolved" and finding.get("resolved_by"):
        return
    if not name:
        report.error(finding.fid, "statut %s sans champ change (resolved accepte resolved_by : commit ou reference)"
                     % finding.get("status"))
        return
    change_dir = find_change_dir(name, openspec_root, audit_dir)
    if change_dir is None:
        report.error(finding.fid, "changement introuvable : %s (cherche dans %s, archive et changes-draft)"
                     % (name, openspec_root / "changes"))
        return
    check_change_trace(finding, change_dir, report)


def check_duplicates(findings, report):
    titles, evidences = {}, {}
    for finding in findings:
        title = normalize(str(finding.get("title")))
        if title and title in titles:
            report.warn(finding.fid, "titre identique a %s : doublon possible" % titles[title])
        titles.setdefault(title, finding.fid)
        for path, lines in finding.evidence_files():
            owner = evidences.setdefault((path, lines), finding.fid)
            if lines is not None and owner != finding.fid:
                report.warn(finding.fid, "meme preuve %s:%s que %s : doublon possible" % (path, lines, owner))


def resolve_openspec_root(args, audit_dir, root):
    if args.openspec_root:
        return root / args.openspec_root
    state = audit_dir / "state.md"
    if state.is_file():
        fields, _error = parse_front_matter(state.read_text(encoding="utf-8"))
        if fields and fields.get("openspec_root"):
            return root / fields["openspec_root"]
    return root / "openspec"


def run_checks(findings, root, audit_dir, openspec_root):
    report = Report()
    if not (audit_dir / "state.md").is_file():
        report.warn("state.md", "absent : etat de l'analyse non enregistre")
    valid, files_by_id = [], {}
    for finding in findings:
        if finding.error:
            report.error(finding.path.name, finding.error)
            continue
        valid.append(finding)
        if finding.fid in files_by_id:
            report.error(finding.fid, "identifiant en double (%s et %s)" % (files_by_id[finding.fid], finding.path.name))
        files_by_id[finding.fid] = finding.path.name
    for finding in valid:
        check_fields(finding, report)
        check_evidence(finding, root, report)
        check_links(finding, files_by_id, openspec_root, audit_dir, report)
    check_duplicates(valid, report)
    if not openspec_root.is_dir() and any(finding.get("change") for finding in valid):
        report.warn("openspec", "racine OpenSpec introuvable (%s) : seuls les brouillons changes-draft/ sont verifies"
                    % openspec_root)
    return valid, report


def summarize(valid, report):
    counts = {}
    for finding in valid:
        key = "%s/%s" % (finding.get("qualification") or "?", finding.get("status") or "?")
        counts[key] = counts.get(key, 0) + 1
    say("%d constat(s) : %s" % (len(valid), ", ".join("%s=%d" % item for item in sorted(counts.items())) or "aucun"))
    say("%d erreur(s), %d avertissement(s)." % (len(report.errors), len(report.warnings)))


def cmd_check(args):
    root, audit_dir = Path(args.root).resolve(), Path(args.audit_dir).resolve()
    findings = findings_or_report(audit_dir)
    if findings is None:
        return 2
    openspec_root = resolve_openspec_root(args, audit_dir, root)
    valid, report = run_checks(findings, root, audit_dir, openspec_root)
    for line in report.errors + report.warnings:
        say(line)
    summarize(valid, report)
    return 1 if report.errors or (args.strict and report.warnings) else 0


# --- snapshot / drift ----------------------------------------------------------------------

def file_digest(path):
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def snapshot_path(audit_dir):
    return audit_dir / SNAPSHOT_NAME


def load_snapshot(audit_dir):
    path = snapshot_path(audit_dir)
    if not path.is_file():
        return {"version": 1, "entries": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_finding(finding, root):
    digests = {}
    for path, _lines in finding.evidence_files():
        if is_unsafe_path(path):
            say("ATTENTION %s : chemin ignore (absolu ou hors du projet) : %s" % (finding.fid, path))
            continue
        digests[path] = file_digest(root / path)
        if digests[path] is None:
            say("ATTENTION %s : fichier-preuve introuvable : %s" % (finding.fid, path))
    return digests


def cmd_snapshot(args):
    root, audit_dir = Path(args.root).resolve(), Path(args.audit_dir).resolve()
    findings = findings_or_report(audit_dir)
    if findings is None:
        return 2
    wanted = {identifier.strip() for identifier in args.ids.split(",")} if args.ids else None
    snapshot = load_snapshot(audit_dir)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    selected = [f for f in findings if not f.error and (wanted is None or f.fid in wanted)]
    for finding in selected:
        snapshot["entries"][finding.fid] = {"recorded_at": now, "files": snapshot_finding(finding, root)}
    snapshot_path(audit_dir).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    say("Empreintes enregistrees pour %d constat(s) dans %s" % (len(selected), SNAPSHOT_NAME))
    return 0


def drift_for_finding(finding, entry, root):
    """Retourne la liste de (probleme, fichiers) pour un constat dont l'empreinte est connue."""
    recorded = entry["files"]
    differing = [path for path, digest in sorted(recorded.items()) if file_digest(root / path) != digest]
    missing = [path for path in differing if not (root / path).is_file()]
    changed = [path for path in differing if path not in missing]
    added = new_evidence_paths(finding, recorded)
    problems = (("changed", changed), ("missing", missing), ("evidence-added", added))
    return [(problem, files) for problem, files in problems if files]


def new_evidence_paths(finding, recorded):
    return [path for path, _lines in finding.evidence_files() if path not in recorded]


DRIFT_LABELS = {"changed": "preuve modifiee", "missing": "preuve disparue",
                "evidence-added": "preuve ajoutee depuis l'empreinte",
                "no-snapshot": "aucune empreinte (lancer snapshot)"}


def collect_drift(findings, snapshot, root):
    result = []
    for finding in findings:
        if finding.error or finding.get("status") == "rejected":
            continue
        entry = snapshot.get(finding.fid)
        problems = [("no-snapshot", [])] if entry is None else drift_for_finding(finding, entry, root)
        result += [{"id": finding.fid, "problem": problem, "files": files} for problem, files in problems]
    return result


def print_drift(result):
    for item in result:
        say(("%s : %s %s" % (item["id"], DRIFT_LABELS[item["problem"]], ", ".join(item["files"]))).rstrip())
    say("%d constat(s) a revoir." % len({item["id"] for item in result}) if result else "Aucune derive.")


def cmd_drift(args):
    root, audit_dir = Path(args.root).resolve(), Path(args.audit_dir).resolve()
    findings = findings_or_report(audit_dir)
    if findings is None:
        return 2
    result = collect_drift(findings, load_snapshot(audit_dir)["entries"], root)
    if args.json:
        say(json.dumps(result, indent=2))
    else:
        print_drift(result)
    return 1 if result else 0


def cmd_next_id(args):
    audit_dir = Path(args.audit_dir).resolve()
    numbers = []
    for path in (audit_dir / "findings").glob("F-*.md"):
        number = re.match(r"^F-(\d+)", path.name)
        if number:
            numbers.append(int(number.group(1)))
    say("F-%03d" % (max(numbers) + 1 if numbers else 1))
    return 0


# --- point d'entree ------------------------------------------------------------------------

def say(text):
    sys.stdout.write(text + "\n")


def _add_check_options(parser):
    parser.add_argument("--openspec-root", help="dossier openspec, relatif a --root (defaut : state.md, sinon openspec)")
    parser.add_argument("--strict", action="store_true", help="les avertissements font echouer")


def _add_snapshot_options(parser):
    parser.add_argument("--ids", help="liste d'identifiants separes par des virgules (defaut : tous)")


def _add_drift_options(parser):
    parser.add_argument("--json", action="store_true", help="sortie JSON")


COMMANDS = (
    ("check", cmd_check, "valide les constats et la tracabilite", _add_check_options),
    ("snapshot", cmd_snapshot, "enregistre l'empreinte des fichiers-preuves", _add_snapshot_options),
    ("drift", cmd_drift, "detecte les preuves modifiees depuis l'empreinte", _add_drift_options),
    ("next-id", cmd_next_id, "prochain identifiant de constat libre", None),
)


def build_parser():
    parser = argparse.ArgumentParser(description="Controles deterministes pour le skill code-to-openspec.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, handler, help_text, add_options in COMMANDS:
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--audit-dir", required=True, help="dossier d'audit (contient findings/)")
        command.add_argument("--root", default=".", help="racine du projet (defaut : dossier courant)")
        command.set_defaults(func=handler)
        if add_options:
            add_options(command)
    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
