#!/usr/bin/env python3
"""Tests de bout en bout : publication, installation et mise à jour, sur des dépôts temporaires.

    python -m unittest discover -s skills/development/install-git-submodule/tests -v

Ils s'appuient sur le skill voisin `publish-git-submodule` (même dossier parent). Ce qu'ils ne
prouvent pas : les permissions GitHub, les secrets et l'exécution réelle des workflows.
"""
from __future__ import annotations

import filecmp
import glob
import json
import os
import py_compile
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SIBLING = os.path.join(os.path.dirname(os.path.dirname(HERE)), "publish-git-submodule", "tests")
if not os.path.isdir(SIBLING):
    raise unittest.SkipTest("skill voisin publish-git-submodule absent")
sys.path.insert(0, SIBLING)
from sandbox import INSTALL, PUBLISH, UPDATE, Sandbox

try:
    import yaml
except ImportError:
    yaml = None

CONFIG = ".github/submodule-update.json"
WORKFLOW = ".github/workflows/submodule-update.yml"
PRODUCER = {
    "app/main.py": "print('application')\n",
    ".claude/CLAUDE.md": "# Instructions\n",
    ".claude/skills/demo/SKILL.md": "---\nname: demo\n---\n",
    "docs/guide.md": "# Guide\n",
}
GITHUB_URL = "https://github.com/acme/producer.git"


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)
        self.source_remote, self.producer = self.box.project("producer", PRODUCER)
        self.consumer_remote, self.consumer = self.box.project("consumer", {"README.md": "# Consommateur\n"})
        self.publish("setup", "source=.claude", "branch=main", "export=submodule/claude", "auto=false")

    def run_script(self, script, cwd, args, env, code):
        proc = self.box.script(script, cwd, *args, env=env)
        self.assertEqual(proc.returncode, code, "sortie :\n%s\n%s" % (proc.stdout, proc.stderr))
        self.assertNotIn("Traceback", proc.stderr)
        return proc

    def publish(self, *args, code=0):
        return self.run_script(PUBLISH, self.producer, args, None, code)

    def install(self, *args, code=0, env=None):
        return self.run_script(INSTALL, self.consumer, ("apply",) + args, env, code)

    def update(self, *args, code=0, env=None):
        return self.run_script(UPDATE, self.consumer, ("run",) + args, env, code)

    def install_claude(self, *extra, code=0):
        return self.install("url=" + self.source_remote, "branch=submodule/claude", "target=.claude",
                            "auto=true", "commit=true", "push=true", *extra, code=code)

    def release(self, text, rel=".claude/CLAUDE.md"):
        """Nouvelle version côté producteur, publiée sur sa branche d'export."""
        self.box.write(self.producer, rel, text)
        self.box.commit(self.producer, "nouvelle version")
        self.publish("run", "--all", "--push")
        return self.box.remote_sha(self.source_remote, "submodule/claude")

    def recorded(self, path=".claude", ref="main"):
        return self.box.git(self.consumer_remote, "ls-tree", ref, "--", path).split()[2]

    def head(self):
        return self.box.git(self.consumer, "rev-parse", "HEAD")

    def set_config(self, **changes):
        path = os.path.join(self.consumer, CONFIG)
        data = json.loads(self.box.read(self.consumer, CONFIG))
        for key, value in changes.items():
            if key == "submodule":
                data["submodules"][0].update(value)
            else:
                data[key] = value
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2)
        self.box.commit(self.consumer, "configuration des mises à jour")


class InstallAndAdopt(EndToEnd):
    def test_install_then_adopt_a_new_version(self):
        self.install_claude()
        self.assertTrue(os.path.isfile(os.path.join(self.consumer, ".claude", "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(self.consumer, ".claude", ".claude")))
        self.assertFalse(os.path.exists(os.path.join(self.consumer, ".claude", "app")))
        branch = self.box.git(self.consumer, "config", "-f", ".gitmodules", "submodule..claude.branch")
        self.assertEqual(branch, "submodule/claude")
        first = self.box.remote_sha(self.source_remote, "submodule/claude")
        self.assertEqual(self.recorded(), first)
        self.assertEqual(json.loads(self.box.read(self.consumer, CONFIG))["target_branch"], "main")

        second = self.release("# Instructions v2\n")
        before = self.head()
        self.update("--push")
        self.assertEqual(self.recorded(), second)
        self.assertEqual(self.box.read(self.consumer, ".claude/CLAUDE.md"), "# Instructions v2\n")
        # Un seul commit, qui ne contient que la référence du sous-module.
        self.assertEqual(self.box.git(self.consumer, "rev-parse", "HEAD^"), before)
        self.assertEqual(self.box.git(self.consumer, "show", "--name-only", "--format=", "HEAD"), ".claude")
        message = self.box.git(self.consumer, "log", "-1", "--format=%B")
        self.assertIn("Submodule-Old: " + first, message)
        self.assertIn("Submodule-New: " + second, message)

        # Rien de neuf : aucun commit.
        after = self.head()
        self.assertIn("unchanged", self.update("--push").stdout)
        self.assertEqual(self.head(), after)
        self.assertEqual(self.box.remote_sha(self.consumer_remote, "main"), after)

    def test_whole_repository_as_submodule(self):
        self.publish("setup", "source=.", "branch=main", "auto=false")
        self.install("url=" + self.source_remote, "branch=main", "target=vendor/tool", "commit=true", "push=true")
        self.assertTrue(os.path.isfile(os.path.join(self.consumer, "vendor", "tool", "app", "main.py")))
        self.box.write(self.producer, "app/main.py", "print('v2')\n")
        tip = self.box.commit(self.producer, "v2")
        self.update("--push")
        self.assertEqual(self.recorded("vendor/tool"), tip)

    def test_several_submodules_and_a_target_with_spaces(self):
        self.publish("setup", "source=docs", "branch=main", "export=submodule/docs", "auto=false")
        self.install_claude()
        self.install("url=" + self.source_remote, "branch=submodule/docs", "target=shared libs/my docs",
                     "commit=true", "push=true")
        self.assertTrue(os.path.isfile(os.path.join(self.consumer, "shared libs", "my docs", "guide.md")))
        managed = [e["path"] for e in json.loads(self.box.read(self.consumer, CONFIG))["submodules"]]
        self.assertEqual(managed, [".claude", "shared libs/my docs"])
        claude = self.recorded()
        before = self.head()
        self.box.write(self.producer, "docs/guide.md", "# Guide v2\n")
        self.box.commit(self.producer, "guide v2")
        self.publish("run", "--all", "--push")
        self.update("--push")
        self.assertEqual(self.recorded("shared libs/my docs"), self.box.remote_sha(self.source_remote, "submodule/docs"))
        self.assertEqual(self.recorded(), claude)
        self.assertEqual(self.box.git(self.consumer, "rev-list", "--count", before + "..HEAD"), "1")

    def test_reinstall_verifies_and_conflicting_requests_ask(self):
        self.install_claude()
        head = self.head()
        self.assertIn("verified", self.install_claude().stdout)
        self.assertEqual(self.head(), head)
        self.assertEqual(self.box.git(self.consumer, "status", "--porcelain"), "")
        proc = self.install("url=" + self.source_remote, "branch=main", "target=.claude", code=7)
        self.assertIn("set-branch=true", proc.stderr)
        proc = self.install("url=" + self.consumer_remote, "branch=main", "target=.claude", code=7)
        self.assertIn("set-url=true", proc.stderr)
        self.assertEqual(self.head(), head)

    def test_failed_add_leaves_the_repository_untouched(self):
        # Un dépôt de module resté d'un essai précédent fait échouer `git submodule add`.
        os.makedirs(os.path.join(self.consumer, ".git", "modules", ".claude"))
        self.box.write(self.consumer, ".git/modules/.claude/HEAD", "ref: refs/heads/main\n")
        self.install_claude(code=1)
        self.assertEqual(self.box.git(self.consumer, "status", "--porcelain"), "")
        self.assertFalse(os.path.exists(os.path.join(self.consumer, ".gitmodules")))
        self.assertFalse(os.path.exists(os.path.join(self.consumer, ".claude")))

    def test_wrong_branch_would_nest_the_folder(self):
        proc = self.install("url=" + self.source_remote, "branch=main", "target=.claude", code=7)
        self.assertIn(".claude/.claude", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.consumer, ".claude")))

    def test_unknown_branch_and_unsafe_parameters(self):
        proc = self.install("url=" + self.source_remote, "branch=submodule/absent", "target=.claude", code=3)
        self.assertIn("submodule/claude", proc.stderr)
        for target in ("../x", "/tmp/x", "a/../../b", ".git/modules/x", "x;touch pwned", ":(icase)readme.md"):
            self.install("url=" + self.source_remote, "branch=submodule/claude", "target=" + target, code=2)
        self.install("url=https://user:secret@example.invalid/a/b.git", "branch=main", "target=x", code=2)
        self.install("url=--upload-pack=touch pwned", "branch=main", "target=x", code=2)
        self.assertEqual(self.box.git(self.consumer, "status", "--porcelain"), "")

    def test_a_submodule_cannot_be_republished_as_a_folder(self):
        self.install_claude()
        proc = self.run_script(PUBLISH, self.consumer, ("setup", "source=.claude", "branch=main"), None, 2)
        self.assertIn("déjà un sous-module", proc.stderr)


class ExistingTarget(EndToEnd):
    def test_identical_folder_is_migrated_with_a_backup(self):
        self.box.write(self.consumer, ".claude/CLAUDE.md", "# Instructions\n")
        self.box.write(self.consumer, ".claude/skills/demo/SKILL.md", "---\nname: demo\n---\n")
        self.box.commit(self.consumer, "copie manuelle")
        proc = self.install_claude()
        self.assertIn("migrated", proc.stdout)
        self.assertEqual(self.recorded(), self.box.remote_sha(self.source_remote, "submodule/claude"))
        backups = glob.glob(os.path.join(self.consumer, ".git", "submodule-sync-backups", "*", "files", "CLAUDE.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.box.git(self.consumer, "status", "--porcelain"), "")

    def test_divergent_folder_asks_then_preserves_every_file(self):
        self.box.write(self.consumer, ".claude/CLAUDE.md", "# Instructions du projet\n")
        self.box.write(self.consumer, ".claude/project-rules.md", "règles propres au projet\n")
        self.box.commit(self.consumer, "configuration du projet")
        self.box.write(self.consumer, ".claude/settings.local.json", '{"local": true}\n')
        self.box.write(self.consumer, ".claude/project-rules.md", "règles modifiées, non commitées\n")
        head, status = self.head(), self.box.git(self.consumer, "status", "--porcelain")

        proc = self.install_claude(code=7)
        for expected in ("CLAUDE.md", "project-rules.md", "settings.local.json", "migrate=preserve"):
            self.assertIn(expected, proc.stdout + proc.stderr)
        self.assertEqual((self.head(), self.box.git(self.consumer, "status", "--porcelain")), (head, status))
        self.assertEqual(self.box.read(self.consumer, ".claude/CLAUDE.md"), "# Instructions du projet\n")
        self.assertFalse(os.path.isdir(os.path.join(self.consumer, ".git", "submodule-sync-backups")))

        self.install_claude("migrate=preserve")
        backup = glob.glob(os.path.join(self.consumer, ".git", "submodule-sync-backups", "*"))[0]

        def saved(rel):
            with open(os.path.join(backup, "files", rel), encoding="utf-8") as fh:
                return fh.read()

        self.assertEqual(saved("CLAUDE.md"), "# Instructions du projet\n")
        self.assertEqual(saved("project-rules.md"), "règles modifiées, non commitées\n")
        self.assertEqual(saved("settings.local.json"), '{"local": true}\n')
        self.assertTrue(os.path.isfile(os.path.join(backup, "tracked-changes.patch")))
        # La source s'installe ; les fichiers propres au projet restent sur place, non suivis.
        self.assertEqual(self.box.read(self.consumer, ".claude/CLAUDE.md"), "# Instructions\n")
        self.assertEqual(self.box.read(self.consumer, ".claude/settings.local.json"), '{"local": true}\n')
        self.assertEqual(self.box.read(self.consumer, ".claude/project-rules.md"), "règles modifiées, non commitées\n")
        # Rien n'est parti vers la source partagée.
        self.assertEqual(self.box.remote_tree(self.source_remote, "submodule/claude"),
                         ["CLAUDE.md", "skills/demo/SKILL.md"])
        # Des fichiers non suivis dans le sous-module n'empêchent pas la mise à jour suivante.
        new = self.release("# Instructions v2\n")
        self.update("--push")
        self.assertEqual(self.recorded(), new)
        self.assertEqual(self.box.read(self.consumer, ".claude/settings.local.json"), '{"local": true}\n')


class UpdateSafety(EndToEnd):
    def setUp(self):
        super().setUp()
        self.install_claude()
        self.first = self.recorded()

    def test_local_changes_in_the_submodule_are_never_overwritten(self):
        self.box.write(self.consumer, ".claude/CLAUDE.md", "travail local en cours\n")
        self.release("# Instructions v2\n")
        head = self.head()
        proc = self.update("--push", code=7)
        self.assertIn("rien n'est écrasé", proc.stderr)
        self.assertEqual(self.box.read(self.consumer, ".claude/CLAUDE.md"), "travail local en cours\n")
        self.assertEqual((self.head(), self.recorded()), (head, self.first))

        # Même garde pour un commit local dans le sous-module.
        sub = os.path.join(self.consumer, ".claude")
        self.box.git(sub, "commit", "-q", "-am", "commit local")
        local = self.box.git(sub, "rev-parse", "HEAD")
        self.update("--push", code=7)
        self.assertEqual(self.box.git(sub, "rev-parse", "HEAD"), local)
        self.assertEqual(self.recorded(), self.first)

    def test_failed_check_publishes_nothing_and_sees_no_token(self):
        self.box.write(self.consumer, "check.py", (
            "import json, os, sys\n"
            "json.dump(sorted(os.environ), open('seen-env.json', 'w'))\n"
            "sys.exit(0 if 'v3' in open('.claude/CLAUDE.md').read() else 1)\n"))
        self.set_config(checks=['"%s" check.py' % sys.executable])
        self.box.git(self.consumer, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.release("# Instructions v2\n")
        head = self.head()
        proc = self.update("--push", code=1, env={"GITHUB_TOKEN": "jeton-de-test", "SUBMODULE_PUSH_TOKEN": "autre"})
        self.assertIn("contrôle échoué", proc.stderr)
        self.assertEqual((self.head(), self.recorded()), (head, self.first))
        self.assertEqual(self.box.git(os.path.join(self.consumer, ".claude"), "rev-parse", "HEAD"), self.first)
        self.assertEqual(self.box.git(self.consumer, "status", "--porcelain", "--untracked-files=no"), "")
        seen = json.loads(self.box.read(self.consumer, "seen-env.json"))
        self.assertIn("SUBMODULE_NEW_SHA", seen)
        self.assertFalse([k for k in seen if "TOKEN" in k.upper() or k.startswith("GIT_CONFIG_")])
        # Le contrôle passe sur la version suivante : elle est adoptée.
        third = self.release("# Instructions v3\n")
        self.update("--push")
        self.assertEqual(self.recorded(), third)

    def test_rewritten_export_is_not_followed_backwards(self):
        root = self.box.git(self.producer, "rev-list", "--max-parents=0", "HEAD")
        self.box.git(self.producer, "reset", "-q", "--hard", root)
        self.box.write(self.producer, ".claude/CLAUDE.md", "# Histoire réécrite\n")
        self.box.git(self.producer, "add", "-A")
        self.box.git(self.producer, "commit", "-q", "--amend", "-m", "réécrit")
        self.box.git(self.producer, "push", "-q", "--force", "origin", "HEAD:refs/heads/main")
        self.publish("setup", "source=.claude", "branch=main", "export=submodule/claude", "auto=false", "force=true")
        proc = self.update("--push", code=4)
        self.assertIn("Aucun retour en arrière automatique", proc.stderr)
        self.assertEqual(self.recorded(), self.first)
        self.set_config(submodule={"allow_non_fast_forward": True})
        self.box.git(self.consumer, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.update("--push")
        self.assertEqual(self.recorded(), self.box.remote_sha(self.source_remote, "submodule/claude"))

    def test_hold_freezes_a_pinned_reference(self):
        self.set_config(submodule={"hold": True})
        self.release("# Instructions v2\n")
        self.assertIn("held", self.update().stdout)
        self.assertEqual(self.box.git(self.consumer, "ls-tree", "HEAD", "--", ".claude").split()[2], self.first)

    def test_rejected_push_is_rebased_never_forced(self):
        other = self.box.clone(self.consumer_remote, "colleague")
        self.box.write(other, "feature.txt", "travail d'un collègue\n")
        theirs = self.box.commit(other, "travail concurrent")
        new = self.release("# Instructions v2\n")
        self.update("--push")
        self.assertEqual(self.recorded(), new)
        self.box.git(self.consumer_remote, "merge-base", "--is-ancestor", theirs, "main")

    def test_pull_request_mode_leaves_the_protected_branch_alone(self):
        stub, calls = self.box.path("gh_stub.py"), self.box.path("gh-calls.jsonl")
        with open(stub, "w", encoding="utf-8") as fh:
            fh.write("import json, os, sys\n"
                     "open(os.environ['GH_STUB_LOG'], 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
                     "print('[]' if sys.argv[1:3] == ['pr', 'list'] else '')\n")
        self.set_config(mode="pr")
        self.box.git(self.consumer, "push", "-q", "origin", "HEAD:refs/heads/main")
        main = self.box.remote_sha(self.consumer_remote, "main")
        new = self.release("# Instructions v2\n")
        env = {"SUBMODULE_SYNC_GH": json.dumps([sys.executable, stub]), "GH_STUB_LOG": calls}
        proc = self.update("--push", env=env)
        self.assertIn("pull request submodule-update/main-", proc.stdout)
        self.assertEqual(self.box.remote_sha(self.consumer_remote, "main"), main)
        heads = self.box.git(self.consumer_remote, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        branch = [h for h in heads.split("\n") if h.startswith("submodule-update/main-")]
        self.assertEqual(len(branch), 1)
        self.assertEqual(self.recorded(ref=branch[0]), new)
        with open(calls, encoding="utf-8") as fh:
            logged = [json.loads(line) for line in fh]
        self.assertEqual([c[:2] for c in logged], [["pr", "list"], ["pr", "create"], ["pr", "merge"]])
        self.assertIn("--auto", logged[2])
        # Tant que la pull request attend, une nouvelle exécution ne casse pas : même branche, pas de second push.
        self.box.git(self.consumer, "reset", "-q", "--hard", main)
        self.box.git(self.consumer, "submodule", "update", "-q")
        self.update("--push", env=env)
        self.assertEqual(self.recorded(ref=branch[0]), new)
        self.assertEqual(self.box.remote_sha(self.consumer_remote, "main"), main)


class Events(EndToEnd):
    """Le sous-module porte une URL GitHub, résolue vers le remote local par `insteadOf`."""

    def setUp(self):
        super().setUp()
        env = dict(self.box.env)
        count = int(env["GIT_CONFIG_COUNT"])
        env["GIT_CONFIG_KEY_%d" % count] = "url.%s.insteadOf" % self.source_remote.replace(os.sep, "/")
        env["GIT_CONFIG_VALUE_%d" % count] = GITHUB_URL
        env["GIT_CONFIG_COUNT"] = str(count + 1)
        self.box.env = env
        self.install("url=" + GITHUB_URL, "branch=submodule/claude", "target=.claude", "commit=true", "push=true")
        self.first = self.recorded()

    def event(self, sha, repo="acme/producer", branch="submodule/claude", **extra):
        payload = dict({"source_repo": repo, "branch": branch, "sha": sha}, **extra)
        return {"SUBMODULE_EVENT_PAYLOAD": json.dumps(payload)}

    def test_event_adopts_the_branch_head_and_records_the_source_commit(self):
        second = self.release("# Instructions v2\n")
        source = self.box.git(self.producer, "rev-parse", "HEAD")
        self.update("--push", env=self.event(second, source_sha=source))
        self.assertEqual(self.recorded(), second)
        self.assertIn("Source-Commit: " + source, self.box.git(self.consumer, "log", "-1", "--format=%B"))

    def test_duplicate_and_stale_events_change_nothing(self):
        second = self.release("# Instructions v2\n")
        third = self.release("# Instructions v3\n")
        # Événement en retard : il annonce v2 alors que la branche est déjà à v3.
        proc = self.update("--push", env=self.event(second))
        self.assertIn("c'est la branche qui fait foi", proc.stdout)
        self.assertEqual(self.recorded(), third)
        head = self.head()
        for stale in (second, third, self.first):
            self.assertIn("unchanged", self.update("--push", env=self.event(stale)).stdout)
        self.assertEqual((self.head(), self.recorded()), (head, third))
        self.assertEqual(self.box.remote_sha(self.consumer_remote, "main"), head)

    def test_foreign_or_malformed_events_are_rejected(self):
        second = self.release("# Instructions v2\n")
        head = self.head()
        for env in (self.event(second, repo="evil/producer"), self.event(second, branch="main")):
            self.assertIn("événement ignoré", self.update("--push", env=env).stdout)
        for env in (self.event("$(touch pwned)"), self.event(second, branch="x; rm -rf ."),
                    self.event(second, repo="../../etc"), {"SUBMODULE_EVENT_PAYLOAD": "[1, 2]"},
                    {"SUBMODULE_EVENT_PAYLOAD": "{pas du json"}):
            self.update("--push", env=env, code=2)
        self.assertEqual((self.head(), self.recorded()), (head, self.first))
        self.assertFalse(os.path.exists(os.path.join(self.consumer, "pwned")))


class StaticChecks(EndToEnd):
    def test_scripts_compile_and_the_shared_module_is_identical(self):
        scripts = os.path.dirname(INSTALL)
        for name in ("install.py", "update.py", "submodule_common.py"):
            py_compile.compile(os.path.join(scripts, name), doraise=True)
        self.assertTrue(filecmp.cmp(os.path.join(scripts, "submodule_common.py"),
                                    os.path.join(os.path.dirname(PUBLISH), "submodule_common.py"), shallow=False))

    @unittest.skipIf(yaml is None, "PyYAML absent")
    def test_generated_workflow_is_valid_yaml(self):
        self.install_claude("schedule=41 3 * * *", "check=python -m compileall -q .")
        data = yaml.safe_load(self.box.read(self.consumer, WORKFLOW))
        triggers = data.get("on", data.get(True))
        self.assertEqual(triggers["repository_dispatch"]["types"], ["submodule-updated"])
        self.assertEqual(triggers["schedule"], [{"cron": "41 3 * * *"}])
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(data["permissions"], {"contents": "write"})
        self.assertFalse(data["concurrency"]["cancel-in-progress"])
        checkout, step = data["jobs"]["update"]["steps"]
        self.assertEqual(checkout["with"], {"ref": "main", "persist-credentials": False, "submodules": False})
        # Tout ce qui vient de l'événement passe par l'environnement, pas par le texte du script.
        self.assertNotIn("${{", step["run"])
        self.assertIn("client_payload", step["env"]["SUBMODULE_EVENT_PAYLOAD"])
        self.install_claude("schedule=none", "mode=pr")
        data = yaml.safe_load(self.box.read(self.consumer, WORKFLOW))
        self.assertNotIn("schedule", data.get("on", data.get(True)))
        self.assertEqual(data["permissions"], {"contents": "write", "pull-requests": "write"})


if __name__ == "__main__":
    unittest.main()
