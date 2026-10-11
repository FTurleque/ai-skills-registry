#!/usr/bin/env python3
"""Tests de publish.py sur des dépôts temporaires et des remotes bare locaux.

    python -m unittest discover -s skills/development/publish-git-submodule/tests -v

Ce que ces tests ne prouvent pas : les permissions GitHub et l'exécution réelle des workflows.
"""
from __future__ import annotations

import http.server
import json
import os
import py_compile
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import COMMON, PUBLISH, Sandbox

try:
    import yaml
except ImportError:
    yaml = None

FILES = {
    "app/main.py": "print('application')\n",
    ".claude/CLAUDE.md": "# Instructions\n",
    ".claude/skills/demo/SKILL.md": "---\nname: demo\n---\n",
    "docs/guide.md": "# Guide\n",
    "my docs/notes.md": "# Notes\n",
}
WORKFLOW = ".github/workflows/submodule-publish.yml"
CONFIG = ".github/submodule-publish.json"


class PublishCase(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)
        self.remote, self.repo = self.box.project("producer", FILES)

    def publish(self, *args, env=None, code=0):
        proc = self.box.script(PUBLISH, self.repo, *args, env=env)
        self.assertEqual(proc.returncode, code, "sortie :\n%s\n%s" % (proc.stdout, proc.stderr))
        return proc

    def setup_claude(self, *extra, code=0):
        return self.publish("setup", "source=.claude", "branch=main", "export=submodule/claude",
                            "auto=true", "commit=true", "push=true", *extra, code=code)

    def config(self):
        return json.loads(self.box.read(self.repo, CONFIG))


class FolderExport(PublishCase):
    def test_export_holds_folder_content_at_root(self):
        before = self.box.remote_sha(self.remote, "main")
        proc = self.setup_claude()
        tree = self.box.remote_tree(self.remote, "submodule/claude")
        self.assertEqual(tree, ["CLAUDE.md", "skills/demo/SKILL.md"])
        self.assertFalse([p for p in tree if p.startswith((".claude", "app"))])
        # La branche source ne reçoit que le commit de configuration, par-dessus l'ancien.
        self.assertEqual(self.box.git(self.remote, "rev-parse", "main^"), before)
        changed = self.box.git(self.remote, "show", "--name-only", "--format=", "main").split("\n")
        self.assertEqual(sorted(changed), sorted([
            CONFIG, WORKFLOW, ".github/submodule-sync/PUBLISH.md",
            ".github/submodule-sync/publish.py", ".github/submodule-sync/submodule_common.py"]))
        self.assertIn("/install-git-submodule url=", proc.stdout)
        self.assertIn("branch=submodule/claude target=.claude", proc.stdout)

    def test_rerun_creates_nothing(self):
        self.setup_claude()
        export, main = self.box.remote_sha(self.remote, "submodule/claude"), self.box.remote_sha(self.remote, "main")
        self.assertIn("inchangé", self.publish("run", "--all", "--push").stdout)
        self.assertIn("inchangé", self.setup_claude().stdout)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), export)
        self.assertEqual(self.box.remote_sha(self.remote, "main"), main)
        self.assertEqual(self.box.git(self.repo, "status", "--porcelain"), "")

    def test_change_and_deletion_fast_forward(self):
        self.setup_claude()
        old = self.box.remote_sha(self.remote, "submodule/claude")
        self.box.write(self.repo, ".claude/CLAUDE.md", "# Instructions v2\n")
        os.remove(os.path.join(self.repo, ".claude", "skills", "demo", "SKILL.md"))
        self.box.commit(self.repo, "v2")
        self.assertIn("mis à jour", self.publish("run", "--all", "--push").stdout)
        new = self.box.remote_sha(self.remote, "submodule/claude")
        self.assertEqual(self.box.remote_tree(self.remote, "submodule/claude"), ["CLAUDE.md"])
        self.box.git(self.remote, "merge-base", "--is-ancestor", old, new)

    def test_split_runs_from_another_checkout(self):
        """La publication part du commit distant, quel que soit l'état du poste."""
        self.box.git(self.repo, "checkout", "-q", "--orphan", "scratch")
        self.box.git(self.repo, "rm", "-rfq", ".")
        self.box.write(self.repo, "other.txt", "x\n")
        self.box.git(self.repo, "add", "-A")
        self.box.git(self.repo, "commit", "-q", "-m", "scratch")
        self.publish("setup", "source=.claude", "branch=main", "export=submodule/claude", "auto=false")
        self.assertEqual(self.box.remote_tree(self.remote, "submodule/claude"), ["CLAUDE.md", "skills/demo/SKILL.md"])

    def test_untracked_and_unpushed_work_is_not_published(self):
        self.box.write(self.repo, ".claude/draft.md", "brouillon\n")
        proc = self.setup_claude()
        self.assertNotIn("draft.md", self.box.remote_tree(self.remote, "submodule/claude"))
        self.assertIn("non publiés", proc.stdout)

    def test_missing_folder_keeps_existing_export(self):
        self.setup_claude()
        export = self.box.remote_sha(self.remote, "submodule/claude")
        self.box.git(self.repo, "rm", "-rq", ".claude")
        self.box.commit(self.repo, "supprime .claude")
        proc = self.publish("run", "--all", "--push", code=2)
        self.assertIn("n'existe pas dans le commit source", proc.stderr)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), export)


class WholeRepoAndMany(PublishCase):
    def test_whole_repository_needs_no_export_branch(self):
        proc = self.publish("setup", "source=.", "branch=main", "auto=true", "commit=true", "push=true")
        self.assertIn("dépôt entier", proc.stdout)
        heads = self.box.git(self.remote, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        self.assertEqual(heads, "main")
        workflow = self.box.read(self.repo, WORKFLOW)
        self.assertNotIn("paths:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("branch=main target=<chemin-cible>", proc.stdout)

    def test_several_publications_and_a_path_with_spaces(self):
        self.setup_claude()
        self.publish("setup", "source=docs", "branch=main", "export=submodule/docs", "commit=true", "push=true")
        self.publish("setup", "source=my docs", "branch=main", "commit=true", "push=true")
        self.assertEqual(self.box.remote_tree(self.remote, "submodule/docs"), ["guide.md"])
        self.assertEqual(self.box.remote_tree(self.remote, "submodule/my-docs"), ["notes.md"])
        self.assertEqual([p["name"] for p in self.config()["publications"]], ["claude", "docs", "my-docs"])
        workflow = self.box.read(self.repo, WORKFLOW)
        for path in ('".claude/**"', '"docs/**"', '"my docs/**"', '".github/submodule-publish.json"'):
            self.assertIn(path, workflow)
        # Une seule des trois change : les deux autres ne bougent pas.
        claude, docs = (self.box.remote_sha(self.remote, b) for b in ("submodule/claude", "submodule/docs"))
        self.box.write(self.repo, "my docs/notes.md", "# Notes v2\n")
        self.box.commit(self.repo, "notes v2")
        self.publish("run", "--all", "--push")
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), claude)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/docs"), docs)
        self.assertEqual(self.box.git(self.remote, "show", "submodule/my-docs:notes.md"), "# Notes v2")

    def test_export_branch_collisions_are_refused(self):
        self.setup_claude()
        for export in ("main", "submodule/claude", "submodule/claude/deep", "submodule"):
            proc = self.publish("setup", "source=docs", "branch=main", "export=" + export, code=2)
            self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(len(self.config()["publications"]), 1)


class ParameterSafety(PublishCase):
    def test_paths_leaving_the_repository_are_refused(self):
        for source in ("../outside", "docs/../../x", "/etc", "C:/Windows", "docs;rm -rf x", "$(id)", ".git/hooks"):
            proc = self.publish("setup", "source=" + source, "branch=main", "dry-run=true", code=2)
            self.assertNotIn("Traceback", proc.stderr)
        self.publish("setup", "source=docs", "branch=main; echo x", "dry-run=true", code=2)
        self.assertEqual(self.box.remote_sha(self.remote, "main"), self.box.git(self.repo, "rev-parse", "HEAD"))

    def test_dry_run_writes_nothing(self):
        proc = self.publish("setup", "source=.claude", "branch=main", "dry-run=true")
        self.assertIn("serait créée", proc.stdout)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), "")
        self.assertEqual(self.box.git(self.repo, "status", "--porcelain"), "")


class SensitiveContent(PublishCase):
    def test_local_settings_block_then_history_blocks_then_snapshot_publishes(self):
        self.box.write(self.repo, ".claude/settings.local.json", '{"permissions": {}}\n')
        self.box.commit(self.repo, "réglages locaux commités par erreur")
        proc = self.setup_claude(code=5)
        self.assertIn("[local-settings] settings.local.json", proc.stderr)
        self.assertIn("dernier commit", proc.stderr)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), "")
        self.assertFalse(os.path.exists(os.path.join(self.repo, CONFIG)))

        # Retirer le fichier ne l'efface pas de l'historique qu'une extraction subtree publierait.
        self.box.git(self.repo, "rm", "-q", ".claude/settings.local.json")
        self.box.commit(self.repo, "retire les réglages locaux")
        proc = self.setup_claude(code=5)
        self.assertIn("historique publié", proc.stderr)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), "")

        self.setup_claude("strategy=snapshot")
        objects = self.box.git(self.remote, "rev-list", "--objects", "submodule/claude")
        self.assertNotIn("settings.local.json", objects)
        self.assertEqual(self.box.git(self.remote, "rev-list", "--count", "submodule/claude"), "1")

    def test_secret_value_is_never_printed_and_acceptance_is_recorded(self):
        token = "gh" + "p_" + "A1b2C3d4" * 5
        self.box.write(self.repo, ".claude/mcp.json", '{"token": "%s"}\n' % token)
        self.box.commit(self.repo, "jeton commité par erreur")
        proc = self.setup_claude(code=5)
        self.assertIn("[github-token] mcp.json:1", proc.stderr)
        self.assertNotIn(token, proc.stdout + proc.stderr)
        self.setup_claude("accept-findings=true")
        self.assertEqual(len(self.config()["publications"][0]["accepted_findings"]), 1)
        # Un constat accepté ne rebloque pas ; un nouveau, si.
        self.box.write(self.repo, ".claude/notes.md", "voir " + "C:" + "\\Users\\" + "alice\\projet\n")
        self.box.commit(self.repo, "chemin personnel")
        proc = self.publish("run", "--all", "--push", code=5)
        self.assertIn("[personal-path] notes.md:1", proc.stderr)
        self.assertNotIn("mcp.json", proc.stderr)

    def test_snapshot_excludes_files_and_stays_idempotent(self):
        self.box.write(self.repo, ".claude/settings.local.json", "{}\n")
        self.box.commit(self.repo, "réglages locaux")
        self.setup_claude("strategy=snapshot", "exclude=*.local.json")
        self.assertEqual(self.box.remote_tree(self.remote, "submodule/claude"), ["CLAUDE.md", "skills/demo/SKILL.md"])
        export = self.box.remote_sha(self.remote, "submodule/claude")
        self.box.write(self.repo, ".claude/settings.local.json", '{"a": 1}\n')
        self.box.commit(self.repo, "ne touche que le fichier exclu")
        self.assertIn("inchangé", self.publish("run", "--all", "--push").stdout)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), export)
        self.assertIn("Source-Commit:", self.box.git(self.remote, "log", "-1", "--format=%B", "submodule/claude"))

    def test_snapshot_does_not_take_over_an_unrelated_branch(self):
        self.box.git(self.repo, "push", "-q", "origin", "HEAD:refs/heads/develop")
        develop = self.box.remote_sha(self.remote, "develop")
        proc = self.publish("setup", "source=.claude", "branch=main", "export=develop", "strategy=snapshot", code=7)
        self.assertIn("n'est pas un export de ce skill", proc.stderr)
        self.publish("setup", "source=.claude", "branch=main", "export=develop", code=4)
        self.assertEqual(self.box.remote_sha(self.remote, "develop"), develop)

    def test_exclude_is_refused_with_subtree(self):
        proc = self.setup_claude("exclude=*.local.json", code=2)
        self.assertIn("pas un filtre de fichiers", proc.stderr)


class RewrittenHistory(PublishCase):
    def test_non_fast_forward_is_refused_unless_forced_with_lease(self):
        self.setup_claude()
        export = self.box.remote_sha(self.remote, "submodule/claude")
        root = self.box.git(self.repo, "rev-list", "--max-parents=0", "HEAD")
        self.box.git(self.repo, "reset", "-q", "--hard", root)
        self.box.write(self.repo, ".claude/CLAUDE.md", "# Histoire réécrite\n")
        self.box.git(self.repo, "add", "-A")
        self.box.git(self.repo, "commit", "-q", "--amend", "-m", "initial réécrit")
        self.box.git(self.repo, "push", "-q", "--force", "origin", "HEAD:refs/heads/main")
        proc = self.publish("setup", "source=.claude", "branch=main", "export=submodule/claude", code=4)
        self.assertIn("Rien n'est écrasé par défaut", proc.stderr)
        self.assertEqual(self.box.remote_sha(self.remote, "submodule/claude"), export)
        self.assertIn("réécrit", self.publish("setup", "source=.claude", "branch=main",
                                             "export=submodule/claude", "force=true").stdout)
        self.assertNotEqual(self.box.remote_sha(self.remote, "submodule/claude"), export)


class Notification(PublishCase):
    def setUp(self):
        super().setUp()
        self.requests = []
        case = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                case.requests.append((self.path, self.headers.get("Authorization"), json.loads(body)))
                self.send_response(404 if "missing" in self.path else 204)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.api = {"GITHUB_API_URL": "http://127.0.0.1:%d" % self.server.server_port,
                    "GITHUB_REPOSITORY": "acme/producer", "SUBMODULE_DISPATCH_TOKEN": "jeton-de-test"}

    def test_consumers_are_notified_only_when_the_export_changes(self):
        self.setup_claude()
        self.publish("register", "--name", "claude", "--consumer", "acme/consumer", "--commit")
        self.box.git(self.repo, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.publish("run", "--all", "--push", "--notify", env=self.api)
        self.assertEqual(self.requests, [])

        self.box.write(self.repo, ".claude/CLAUDE.md", "# v2\n")
        source = self.box.commit(self.repo, "v2")
        self.publish("run", "--all", "--push", "--notify", env=self.api)
        self.assertEqual(len(self.requests), 1)
        path, auth, body = self.requests[0]
        self.assertEqual(path, "/repos/acme/consumer/dispatches")
        self.assertEqual(auth, "Bearer jeton-de-test")
        self.assertEqual(body["event_type"], "submodule-updated")
        self.assertEqual(body["client_payload"], {
            "source_repo": "acme/producer", "branch": "submodule/claude", "publication": "claude",
            "sha": self.box.remote_sha(self.remote, "submodule/claude"), "source_sha": source})

        self.publish("run", "--all", "--push", "--notify", env=self.api)
        self.assertEqual(len(self.requests), 1)
        self.publish("run", "--all", "--push", "--notify", "--notify-always", env=self.api)
        self.assertEqual(len(self.requests), 2)

    def test_missing_token_warns_and_failed_dispatch_fails_the_run(self):
        self.setup_claude("consumer=acme/missing")
        self.box.write(self.repo, ".claude/CLAUDE.md", "# v2\n")
        self.box.commit(self.repo, "v2")
        env = dict(self.api, SUBMODULE_DISPATCH_TOKEN="")
        proc = self.publish("run", "--all", "--push", "--notify", env=env)
        self.assertIn("SUBMODULE_DISPATCH_TOKEN est absent", proc.stdout)
        proc = self.publish("run", "--all", "--push", "--notify", "--notify-always", env=self.api, code=1)
        self.assertIn("HTTP 404", proc.stderr)
        self.assertNotIn("jeton-de-test", proc.stdout + proc.stderr)


class StaticChecks(PublishCase):
    def test_scripts_compile(self):
        py_compile.compile(PUBLISH, doraise=True)
        py_compile.compile(COMMON, doraise=True)

    @unittest.skipIf(yaml is None, "PyYAML absent")
    def test_generated_workflow_is_valid_yaml(self):
        self.setup_claude()
        self.publish("setup", "source=my docs", "branch=main", "commit=true")
        data = yaml.safe_load(self.box.read(self.repo, WORKFLOW))
        triggers = data.get("on", data.get(True))
        self.assertEqual(triggers["push"]["branches"], ["main"])
        self.assertIn("my docs/**", triggers["push"]["paths"])
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(data["permissions"], {"contents": "write"})
        self.assertFalse(data["concurrency"]["cancel-in-progress"])
        step = data["jobs"]["publish"]["steps"][-1]
        self.assertEqual(data["jobs"]["publish"]["steps"][0]["with"]["fetch-depth"], 0)
        self.assertIn("publish.py run --all --push --notify", step["run"])
        # Aucune valeur d'événement n'est interpolée dans le texte du script.
        self.assertNotIn("${{", step["run"])


if __name__ == "__main__":
    unittest.main()
