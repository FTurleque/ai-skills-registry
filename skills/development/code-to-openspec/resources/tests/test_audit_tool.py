"""Tests de audit_tool.py (unittest, bibliotheque standard).

Lancer depuis le dossier du skill :
    python -m unittest discover -s resources/tests -v
Chaque test construit son projet dans un dossier temporaire ; ni Git ni le CLI OpenSpec ne sont requis.
"""
import contextlib
import io
import json
import shutil
import importlib.util
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "audit_tool", Path(__file__).resolve().parent.parent / "audit_tool.py")
audit_tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit_tool)

FINDING = """---
id: {id}
title: "{title}"
qualification: {qualification}
status: {status}
priority: P2
priority_rationale: "justifiee"
evidence_level: {level}
evidence:
  - src/app.py:3
  - "run: tests -> ko"
current_behavior: "fait X"
expected_status: {expected_status}
expected_source: "docs/spec.md#x"
minimal_fix: "corriger"
acceptance:
  - "critere"
depends_on: []
change: {change}
requirements:
  - Rounding rule
scenarios:
  - Half rounds up
validated_by: "{validated_by}"
---
"""

DELTA = """# Spec Delta

## ADDED Requirements

### Requirement: Rounding rule
Le systeme SHALL arrondir.

#### Scenario: Half rounds up
- **WHEN** a
- **THEN** b
"""


def with_resolved_by(text, value):
    addition = 'validated_by: ""' + chr(10) + 'resolved_by: "%s"' % value
    return text.replace('validated_by: ""', addition)


def finding(**kw):
    values = dict(id="F-001", title="Titre", qualification="confirmed-defect", status="in-change",
                  level="executed", expected_status="documented", change="fix-it", validated_by="")
    values.update(kw)
    return FINDING.format(**values)


class AuditToolCase(unittest.TestCase):
    def build_project(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_bytes(b"x = 1\n")  # octets : pas de conversion de fin de ligne
        self.audit = self.root / "audit"
        (self.audit / "findings").mkdir(parents=True)
        self.change = self.root / "openspec" / "changes" / "fix-it"
        (self.change / "specs" / "cap").mkdir(parents=True)
        (self.change / "specs" / "cap" / "spec.md").write_text(DELTA, encoding="utf-8")
        (self.change / "proposal.md").write_text("Traite F-001.\n", encoding="utf-8")
        (self.change / "tasks.md").write_text("- [ ] 1.1 Corriger (F-001)\n", encoding="utf-8")
        self.write("F-001-titre.md", finding())

    setUp = build_project  # unittest appelle setUp ; le corps garde un nom snake_case

    def write(self, name, text):
        (self.audit / "findings" / name).write_text(text, encoding="utf-8")

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = audit_tool.main(list(args) + ["--audit-dir", str(self.audit), "--root", str(self.root)])
        return code, out.getvalue()

    def assert_error(self, fragment):
        code, out = self.run_tool("check")
        self.assertEqual(code, 1, out)
        self.assertIn(fragment, out)

    # --- cas valide

    def test_valid_project_passes(self):
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertIn("0 erreur(s)", out)

    # --- vocabulaire et champs

    def test_invalid_priority(self):
        self.write("F-001-titre.md", finding().replace("priority: P2", "priority: P9"))
        self.assert_error("`priority` = 'P9' hors vocabulaire")

    def test_missing_front_matter(self):
        self.write("F-002-sans.md", "pas de front matter\n")
        self.assert_error("front matter absent")

    def test_filename_must_start_with_id(self):
        self.write("F-001-titre.md", finding(id="F-007"))
        self.assert_error("le nom de fichier doit commencer par l'identifiant")

    def test_duplicate_id(self):
        self.write("F-001-bis.md", finding())
        self.assert_error("identifiant en double")

    # --- preuves

    def test_confirmed_defect_needs_strong_evidence(self):
        self.write("F-001-titre.md", finding(level="local-read"))
        self.assert_error("un defaut confirme exige evidence_level executed ou traced")

    def test_executed_needs_run_entry(self):
        self.write("F-001-titre.md", finding().replace('  - "run: tests -> ko"\n', ""))
        self.assert_error("sans entree `run:")

    def test_confirmed_defect_needs_expected(self):
        self.write("F-001-titre.md", finding(expected_status="unknown"))
        self.assert_error("exige un attendu")

    def test_absolute_evidence_path_rejected(self):
        self.write("F-001-titre.md", finding().replace("src/app.py:3", "D:/data/app.py:3"))
        self.assert_error("chemin absolu ou hors du projet")

    def test_parent_directory_path_rejected(self):
        self.write("F-001-titre.md", finding().replace("src/app.py:3", "../secret.py:3"))
        self.assert_error("chemin absolu ou hors du projet")

    def test_missing_evidence_file_is_warning(self):
        self.write("F-001-titre.md", finding().replace("src/app.py:3", "src/gone.py:3"))
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertIn("fichier-preuve introuvable", out)

    # --- tracabilite

    def test_unvalidated_uncertain_expectation_cannot_be_in_change(self):
        self.write("F-001-titre.md", finding(qualification="proposed-improvement", expected_status="proposed"))
        self.assert_error("validated_by")

    def test_validated_proposal_is_accepted(self):
        text = finding(qualification="proposed-improvement", expected_status="proposed", validated_by="D-001")
        self.write("F-001-titre.md", text)
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)

    def test_change_must_exist(self):
        self.write("F-001-titre.md", finding(change="nope"))
        self.assert_error("changement introuvable : nope")

    def test_tasks_must_cite_finding(self):
        (self.change / "tasks.md").write_text("- [ ] 1.1 Corriger\n", encoding="utf-8")
        self.assert_error("tasks.md du changement fix-it ne cite pas F-001")

    def test_unknown_requirement(self):
        self.write("F-001-titre.md", finding().replace("Rounding rule", "Other rule"))
        self.assert_error("exigence introuvable")

    def test_unknown_scenario(self):
        self.write("F-001-titre.md", finding().replace("Half rounds up", "Other scenario"))
        self.assert_error("scenario introuvable")

    def test_unknown_dependency(self):
        self.write("F-001-titre.md", finding().replace("depends_on: []", "depends_on: [F-042]"))
        self.assert_error("depends_on reference un constat inconnu : F-042")

    def test_in_change_requires_change_field(self):
        self.write("F-001-titre.md", finding(change='""'))
        self.assert_error("statut in-change sans champ change")

    def test_resolved_by_replaces_change_for_resolved(self):
        self.write("F-001-titre.md", with_resolved_by(finding(status="resolved", change='""'), "commit abc1234"))
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)

    def test_resolved_without_change_or_resolved_by_fails(self):
        self.write("F-001-titre.md", finding(status="resolved", change='""'))
        self.assert_error("statut resolved sans champ change")

    def test_resolved_by_does_not_bypass_validation_gate(self):
        text = finding(status="resolved", change='""', expected_status="proposed",
                       qualification="proposed-improvement")
        self.write("F-001-titre.md", with_resolved_by(text, "abc"))
        self.assert_error("validated_by")

    def test_archived_change_is_found(self):
        archive = self.root / "openspec" / "changes" / "archive"
        archive.mkdir()
        shutil.move(str(self.change), str(archive / "2026-01-01-fix-it"))
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)

    def test_draft_change_is_found_without_openspec_root(self):
        shutil.rmtree(self.root / "openspec")
        draft = self.audit / "changes-draft" / "fix-it"
        (draft / "specs" / "cap").mkdir(parents=True)
        (draft / "specs" / "cap" / "spec.md").write_text(DELTA, encoding="utf-8")
        (draft / "tasks.md").write_text("- [ ] 1.1 Corriger (F-001)\n", encoding="utf-8")
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertIn("racine OpenSpec introuvable", out)

    def test_no_openspec_warning_without_linked_change(self):
        shutil.rmtree(self.root / "openspec")
        self.write("F-001-titre.md", finding(status="open", change='""'))
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("racine OpenSpec introuvable", out)

    def test_strict_fails_on_warning(self):
        (self.change / "proposal.md").write_text("Ne cite rien.\n", encoding="utf-8")
        self.assertEqual(self.run_tool("check")[0], 0)
        code, _ = self.run_tool("check", "--strict")
        self.assertEqual(code, 1)

    def test_duplicate_titles_warn(self):
        self.write("F-002-autre.md", finding(id="F-002", status="open", change='""'))
        code, out = self.run_tool("check")
        self.assertEqual(code, 0, out)
        self.assertIn("doublon possible", out)

    # --- empreintes et derive

    def test_drift_cycle(self):
        self.assertEqual(self.run_tool("drift")[0], 1)  # pas d'empreinte
        self.assertEqual(self.run_tool("snapshot")[0], 0)
        self.assertEqual(self.run_tool("drift")[0], 0)
        (self.root / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
        code, out = self.run_tool("drift")
        self.assertEqual(code, 1)
        self.assertIn("preuve modifiee src/app.py", out)
        (self.root / "src" / "app.py").unlink()
        code, out = self.run_tool("drift")
        self.assertIn("preuve disparue src/app.py", out)

    def test_line_endings_do_not_cause_drift(self):
        self.run_tool("snapshot")
        (self.root / "src" / "app.py").write_bytes(b"x = 1\r\n")
        self.assertEqual(self.run_tool("drift")[0], 0)

    def test_drift_json(self):
        self.run_tool("snapshot")
        (self.root / "src" / "app.py").write_text("x = 3\n", encoding="utf-8")
        code, out = self.run_tool("drift", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out), [{"id": "F-001", "problem": "changed", "files": ["src/app.py"]}])

    def test_rejected_finding_is_ignored_by_drift(self):
        self.write("F-001-titre.md", finding(status="rejected", change='""'))
        self.assertEqual(self.run_tool("drift")[0], 0)

    # --- identifiants

    def test_next_id(self):
        code, out = self.run_tool("next-id")
        self.assertEqual(out.strip(), "F-002")
        self.write("F-009-x.md", finding(id="F-009"))
        self.assertEqual(self.run_tool("next-id")[1].strip(), "F-010")


if __name__ == "__main__":
    unittest.main()
