"""Tests de adr_tool.py. Lancer : python -m unittest discover -s resources/tests"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import adr_tool


def write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


ARCHGATE_ADR = """---
id: ARCH-001
title: Isolation du domaine
domain: architecture
rules: %s
files: ["domain/**/*.java"]
---

## Decision

**Statut : acceptée (2024-02-05).** Le domaine ne dépend de rien.
"""

NYGARD_ADR = """# 3. Utiliser PostgreSQL

## Statut

Accepté

## Décision

PostgreSQL pour les données métier.
"""


class AdrToolTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="adr-tool-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def kinds(self):
        return [finding["kind"] for finding in adr_tool.run_check(self.root)["findings"]]

    def test_empty_project_has_no_adr_and_no_finding(self):
        write(self.root, "README.md", "# Projet\n")
        result = adr_tool.run_check(self.root)
        self.assertEqual(result["adrs"], [])
        self.assertEqual(result["findings"], [])

    def test_archgate_adr_is_read_from_front_matter_and_body(self):
        write(self.root, ".archgate/adrs/ARCH-001-domain-isolation.md", ARCHGATE_ADR % "true")
        write(self.root, ".archgate/adrs/ARCH-001-domain-isolation.rules.ts", "export default {}\n")
        adr = adr_tool.collect_adrs(self.root)[0]
        self.assertEqual(adr["id"], "ARCH-001")
        self.assertEqual(adr["format"], "archgate")
        self.assertEqual(adr["status"], "accepted")
        self.assertEqual(adr["files"], ["domain/**/*.java"])
        self.assertTrue(adr["rules"] and adr["rules_file"])
        self.assertEqual(self.kinds(), [])

    def test_nygard_adr_status_section_and_numbered_title(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        adr = adr_tool.collect_adrs(self.root)[0]
        self.assertEqual((adr["id"], adr["title"], adr["status"]),
                         ("0003", "Utiliser PostgreSQL", "accepted"))

    def test_templates_readme_and_dependencies_are_not_adrs(self):
        write(self.root, "docs/adr/README.md", "# Registre\n")
        write(self.root, "docs/adr/template.md", "# Titre\n")
        write(self.root, "node_modules/pkg/docs/adr/0001-x.md", NYGARD_ADR)
        write(self.root, "resources/templates/adr.md", "# Gabarit\n")
        self.assertEqual(adr_tool.collect_adrs(self.root), [])

    def test_rules_true_without_companion_file_is_reported(self):
        write(self.root, ".archgate/adrs/ARCH-001-domain-isolation.md", ARCHGATE_ADR % "true")
        self.assertIn("regle-declaree-sans-fichier", self.kinds())

    def test_companion_file_with_rules_false_is_reported(self):
        write(self.root, ".archgate/adrs/ARCH-001-domain-isolation.md", ARCHGATE_ADR % "false")
        write(self.root, ".archgate/adrs/ARCH-001-domain-isolation.rules.ts", "export default {}\n")
        self.assertIn("fichier-de-regle-inactif", self.kinds())

    def test_two_registries_and_close_titles_are_reported(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, ".archgate/adrs/DATA-001-postgres.md",
              "---\nid: DATA-001\ntitle: Persistance PostgreSQL\ndomain: data\nrules: false\n"
              "status: accepted\n---\n")
        kinds = self.kinds()
        self.assertIn("plusieurs-registres", kinds)
        self.assertIn("doublon-possible", kinds)

    def test_duplicate_identifier_is_reported(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/adr/0003-cache-redis.md", NYGARD_ADR.replace("PostgreSQL", "Redis"))
        self.assertIn("identifiant-en-double", self.kinds())

    def test_missing_status_is_reported(self):
        write(self.root, "docs/adr/0005-queue.md", "# 5. File de messages\n\nTexte.\n")
        self.assertIn("statut-indetermine", self.kinds())

    def test_broken_link_is_reported_with_line_and_external_links_ignored(self):
        write(self.root, "docs/adr/0003-use-postgres.md",
              NYGARD_ADR + "\n[absent](./missing.md) [web](https://example.org) [ancre](#x)\n")
        findings = adr_tool.run_check(self.root)["findings"]
        broken = [f for f in findings if f["kind"] == "lien-casse"]
        self.assertEqual(len(broken), 1)
        self.assertRegex(broken[0]["where"], r"0003-use-postgres\.md:\d+$")

    def test_arc42_index_missing_adr_and_status_mismatch(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/adr/0004-queue.md", NYGARD_ADR.replace("3. Utiliser PostgreSQL",
                                                                      "4. File de messages"))
        write(self.root, "docs/arc42/09-architecture-decisions.md",
              "# 9. Décisions d'architecture\n\n| Id | Statut | ADR |\n|---|---|---|\n"
              "| 0003 | Proposée | [0003](../adr/0003-use-postgres.md) |\n")
        result = adr_tool.run_check(self.root)
        self.assertEqual(result["index"], ["docs/arc42/09-architecture-decisions.md"])
        kinds = [finding["kind"] for finding in result["findings"]]
        self.assertIn("adr-absent-de-l-index", kinds)
        self.assertIn("statut-divergent", kinds)

    def test_coherent_registry_and_index_report_nothing(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/arc42/09-architecture-decisions.md",
              "# 9. Décisions d'architecture\n\n| Id | Statut | ADR |\n|---|---|---|\n"
              "| 0003 | Acceptée | [0003](../adr/0003-use-postgres.md) |\n")
        self.assertEqual(self.kinds(), [])

    def test_status_of_a_superseding_adr_stays_accepted(self):
        self.assertEqual(adr_tool.normalize_status("Accepted. Supersedes ADR-0002"), "accepted")
        self.assertEqual(adr_tool.normalize_status("Acceptée, remplace ADR-0002"), "accepted")
        self.assertEqual(adr_tool.normalize_status("Superseded by ADR-0007"), "superseded")
        self.assertEqual(adr_tool.normalize_status("Remplacé par DATA-002"), "superseded")
        self.assertEqual(adr_tool.normalize_status("Remplacée"), "superseded")

    def test_index_status_is_read_from_the_status_column_only(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/arc42/09-architecture-decisions.md",
              "# 9. Décisions d'architecture\n\n| Id | Titre | Statut | ADR |\n|---|---|---|---|\n"
              "| 0003 | Proposer un remplacement du cache | Acceptée |"
              " [0003](../adr/0003-use-postgres.md) |\n")
        self.assertEqual(self.kinds(), [])

    def test_index_without_status_column_reports_no_mismatch(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/arc42/09-architecture-decisions.md",
              "# 9. Décisions d'architecture\n\n- [0003](../adr/0003-use-postgres.md) : proposer"
              " un remplacement\n")
        self.assertEqual(self.kinds(), [])

    def test_first_status_word_wins_in_a_sentence(self):
        sentence = "proposée (2026-10-10).** Remplace DATA-001 une fois acceptée"
        self.assertEqual(adr_tool.normalize_status(sentence), "proposed")
        self.assertEqual(adr_tool.normalize_status("Proposée — remplacerait DATA-001"), "proposed")

    def test_identifier_quoted_in_another_row_status_cell_is_ignored(self):
        write(self.root, "docs/adr/0003-use-postgres.md", NYGARD_ADR)
        write(self.root, "docs/adr/0007-mongo.md",
              "# 7. Stocker les commandes dans MongoDB\n\n## Statut\n\nProposé\n")
        write(self.root, "docs/arc42/09-architecture-decisions.md",
              "# 9. Décisions d'architecture\n\n| Id | Statut | ADR |\n|---|---|---|\n"
              "| 0003 | Acceptée | [0003](../adr/0003-use-postgres.md) |\n"
              "| 0007 | Proposée — remplacerait 0003 | [0007](../adr/0007-mongo.md) |\n")
        self.assertEqual(self.kinds(), [])

    def test_links_in_code_are_examples_not_references(self):
        write(self.root, "docs/adr/0003-use-postgres.md",
              NYGARD_ADR + "\n```markdown\n[exemple](./absent.md)\n```\n\nVoir `[x](./absent.md)`.\n")
        self.assertEqual(self.kinds(), [])

    def test_a_file_named_after_arc42_is_not_an_arc42_folder(self):
        write(self.root, "docs/notes/arc42-openspec.md", "# Notes\n\n[absent](./missing.md)\n")
        result = adr_tool.run_check(self.root)
        self.assertEqual(result["arc42"], [])
        self.assertEqual(result["findings"], [])

    def test_reading_outside_the_project_root_is_refused(self):
        write(self.root, "project/README.md", "# Projet\n")
        write(self.root, "secret.md", "hors projet\n")
        project = os.path.join(self.root, "project")
        self.assertEqual(adr_tool.read_text(project, "README.md"), "# Projet\n")
        with self.assertRaises(ValueError):
            adr_tool.read_text(project, "../secret.md")

    def test_exit_codes(self):
        write(self.root, "docs/adr/0005-queue.md", "# 5. File de messages\n")
        self.assertEqual(adr_tool.main(["inventory", "--root", self.root, "--json"]), 0)
        self.assertEqual(adr_tool.main(["check", "--root", self.root, "--json"]), 1)
        self.assertEqual(adr_tool.main(["check", "--root", os.path.join(self.root, "absent")]), 2)


if __name__ == "__main__":
    unittest.main()
