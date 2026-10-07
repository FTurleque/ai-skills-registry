"""Scenarios de bout en bout du hook : charge utile sur stdin, sortie sur stdout, dans des depots git jetables.

La revue par modele est coupee (SUPERVISOR_NO_LLM). Les sorties sont normalisees (chemins, dates, noms de
rapport, fins de ligne) pour etre identiques d'une machine et d'un systeme a l'autre, puis comparees au
fichier de reference `golden/hook_scenarios.json`."""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BAD = "def f(x):\n    try:\n        x()\n    except Exception:\n        pass\n"
CLEAN = "def add(first, second):\n    return first + second\n"
WARN = "def f():\n    # TODO plus tard\n    return 1\n"      # un constat qui ne bloque pas
TEMP_PREFIX = "scn_"


class Sandbox:
    """Dossier temporaire, depots git jetables, et lancement du superviseur dans un environnement controle."""

    def __init__(self, script: str):
        self.script = script
        self.work = tempfile.mkdtemp(prefix=TEMP_PREFIX)
        self.config_dir = os.path.join(self.work, "cfg")
        os.makedirs(self.config_dir)
        self.env = self._clean_env()

    def _clean_env(self) -> dict:
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.config_dir, SUPERVISOR_NO_LLM="1",
                   GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        # Le hook reel ne recoit ni ces variables ni un stdout UTF-8 : on reproduit son environnement.
        for key in ("CLAUDE_PROJECT_DIR", "SUPERVISOR_ACTIVE", "SUPERVISOR_LOG_DIR", "PYTHONIOENCODING", "PYTHONUTF8"):
            env.pop(key, None)
        return env

    def close(self) -> None:
        shutil.rmtree(self.work, ignore_errors=True)

    def git(self, repo: str, *args: str) -> None:
        subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=self.env)

    def make_repo(self, name: str, files: dict) -> str:
        repo = os.path.join(self.work, name)
        os.makedirs(repo)
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "test@example.invalid")
        self.git(repo, "config", "user.name", "test")
        self.write(repo, "README.md", "x\n")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-qm", "init")
        for rel, text in files.items():
            self.write(repo, rel, text)
        return repo

    @staticmethod
    def write(root: str, rel: str, text: str) -> None:
        with open(os.path.join(root, rel), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def normalize(self, value):
        """Rend une valeur independante de la machine : dossier de travail, separateurs, dates, noms de rapport."""
        if isinstance(value, dict):
            return {key: self.normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.normalize(item) for item in value]
        if not isinstance(value, str):
            return value
        for base in {self.work, os.path.realpath(self.work)}:
            for variant in {base, base.replace("\\", "/")}:
                value = value.replace(variant, "<work>")
        value = re.sub(r"<work>\S*", lambda match: match.group(0).replace("\\", "/"), value)
        value = value.replace("\r\n", "\n")
        value = re.sub(r"rapport-\d{8}-\d{6}", "rapport-<ts>", value)
        value = re.sub(r"Date : [\d-]+ [\d:]+", "Date : <date>", value)
        return re.sub(TEMP_PREFIX + r"\w+", TEMP_PREFIX + "X", value)

    def run(self, repo: str, payload=None, extra_env=None, args=(), raw=None) -> dict:
        env = dict(self.env, CLAUDE_PROJECT_DIR=repo, **(extra_env or {}))
        stdin = raw if raw is not None else json.dumps(payload)
        proc = subprocess.run([sys.executable, self.script, *args], input=stdin.encode("utf-8"), cwd=repo,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        stdout = proc.stdout.decode("utf-8", "replace")
        if stdout.startswith("{"):          # sortie du hook : on compare le JSON, pas sa mise en forme
            stdout = json.loads(stdout)
        return {"rc": proc.returncode, "stdout": self.normalize(stdout),
                "stderr": self.normalize(proc.stderr.decode("utf-8", "replace"))}


def _transcript(sandbox: Sandbox, repo: str) -> str:
    path = os.path.join(sandbox.work, "transcript.jsonl")
    lines = [
        'ligne illisible "tool_use"',
        json.dumps({"message": {"content": [{"type": "tool_use", "name": "Write",
                                             "input": {"file_path": os.path.join(repo, "c.py")}}]}}),
        json.dumps({"message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "zzz.py"}}]}}),
        '{tronque "file_path"',
    ]
    Sandbox.write(sandbox.work, "transcript.jsonl", "\n".join(lines) + "\n")
    return path


def _tomorrow() -> str:
    """Une date de debut de session posterieure a tous les commits du test (git ne date pas l'an 2999)."""
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _commit(sandbox: Sandbox, repo: str, message: str) -> None:
    sandbox.git(repo, "add", ".")
    sandbox.git(repo, "commit", "-qm", message)


def _timestamped_transcript(sandbox: Sandbox, started: str) -> str:
    """Transcript dont la premiere entree date le debut de session (ISO 8601)."""
    path = os.path.join(sandbox.work, "session.jsonl")
    Sandbox.write(sandbox.work, "session.jsonl", json.dumps({"type": "user", "timestamp": started}) + "\n")
    return path


def _failing_reviewer(sandbox: Sandbox) -> str:
    """Faux CLI de revue qui repond comme `claude -p` quand sa session est expiree."""
    script = os.path.join(sandbox.work, "fake_claude.py")
    Sandbox.write(sandbox.work, "fake_claude.py",
                  "import json, sys\nsys.stdin.read()\n"
                  "print(json.dumps({\"is_error\": True, \"result\": \"Failed to authenticate: session expired\"}))\n"
                  "sys.exit(1)\n")
    launcher = os.path.join(sandbox.work, "fake_claude.cmd" if os.name == "nt" else "fake_claude")
    Sandbox.write(sandbox.work, os.path.basename(launcher),
                  ("@echo off\r\n\"%s\" \"%s\"\r\n" if os.name == "nt" else "#!/bin/sh\nexec \"%s\" \"%s\"\n")
                  % (sys.executable, script))
    os.chmod(launcher, 0o755)
    return launcher


def _states(repo: str) -> dict:
    """Etat anti-boucle persiste, sans la duree ni les empreintes (qui dependent du hachage)."""
    folder = os.path.join(repo, "docs", "rapport-supervisor")
    states = {}
    for name in sorted(os.listdir(folder)):
        if name.startswith("state-"):
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                state = json.load(fh)
            state.pop("duration", None)
            state["head"] = bool(state.get("head"))         # un SHA depend du depot jetable : sa presence suffit
            state["reviewed"] = sorted(state.get("reviewed", {}))      # les chemins relus, sans leurs empreintes
            state["rounds_by_signature"] = sorted(state.get("rounds_by_signature", {}).values())
            state["released_signatures"] = len(state.get("released_signatures", []))
            states[name] = state
    return states


def run(script: str) -> dict:
    sandbox = Sandbox(script)
    results = {}
    try:
        bad = sandbox.make_repo("bad", {"a.py": BAD})
        payload = {"cwd": bad, "session_id": "s1", "hook_event_name": "Stop"}
        for round_no in range(1, 5):        # blocage, puis passes jusqu'a la liberation de l'empreinte
            results["bad_round_%d" % round_no] = sandbox.run(bad, payload)
        results["bad_stop_hook_active"] = sandbox.run(bad, dict(payload, stop_hook_active=True))
        results["bad_supervisor_active"] = sandbox.run(bad, payload, {"SUPERVISOR_ACTIVE": "1"})
        results["bad_agent_supervisor"] = sandbox.run(bad, dict(payload, agent_type="code-supervisor"))
        results["bad_other_session"] = sandbox.run(bad, dict(payload, session_id="s2"))
        results["bad_subagent_event"] = sandbox.run(bad, dict(payload, session_id="s3", hook_event_name="SubagentStop"))
        results["invalid_stdin"] = sandbox.run(bad, raw="pas du json")
        results["non_dict_payload"] = sandbox.run(bad, raw="[1, 2]")

        clean = sandbox.make_repo("clean", {"b.py": CLEAN})
        results["clean"] = sandbox.run(clean, {"cwd": clean, "session_id": "c1"})
        unchanged = sandbox.make_repo("unchanged", {})
        results["no_change"] = sandbox.run(unchanged, {"cwd": unchanged, "session_id": "n1"})

        hinted = sandbox.make_repo("hinted", {"a.py": BAD, "c.py": CLEAN})
        transcript = _transcript(sandbox, hinted)
        results["transcript_hint"] = sandbox.run(hinted, {"cwd": hinted, "session_id": "t1", "transcript_path": transcript})
        results["transcript_missing"] = sandbox.run(hinted, {"cwd": hinted, "session_id": "t2",
                                                             "transcript_path": os.path.join(sandbox.work, "absent.jsonl")})

        # Perimetre : un fichier deja commite et inchange n'est plus relu, meme s'il figure dans le transcript.
        committed = sandbox.make_repo("committed", {"a.py": BAD})
        _commit(sandbox, committed, "work")
        committed_hint = os.path.join(sandbox.work, "committed.jsonl")
        Sandbox.write(sandbox.work, "committed.jsonl", json.dumps({"timestamp": _tomorrow(),
            "message": {"content": [{"type": "tool_use", "name": "Write",
                                     "input": {"file_path": os.path.join(committed, "a.py")}}]}}) + "\n")
        results["scope_committed_unchanged"] = sandbox.run(committed, {"cwd": committed, "session_id": "k1",
                                                                        "transcript_path": committed_hint})
        # ... mais ce qui a ete commite depuis le debut de la session (aucun commit avant : arbre vide) est relu.
        started = sandbox.make_repo("started", {"a.py": BAD})
        _commit(sandbox, started, "work")
        results["scope_committed_since_session_start"] = sandbox.run(started, {
            "cwd": started, "session_id": "k2",
            "transcript_path": _timestamped_transcript(sandbox, "2000-01-01T00:00:00.000Z")})
        # Passes successives : le commit de la passe precedente est la base de la suivante.
        stepwise = sandbox.make_repo("stepwise", {"first.py": WARN})
        results["scope_pass_1_uncommitted"] = sandbox.run(stepwise, {"cwd": stepwise, "session_id": "k3"})
        _commit(sandbox, stepwise, "first")
        results["scope_pass_2_nothing_new"] = sandbox.run(stepwise, {"cwd": stepwise, "session_id": "k3"})
        Sandbox.write(stepwise, "second.py", BAD)
        _commit(sandbox, stepwise, "second")
        results["scope_pass_3_commit_since"] = sandbox.run(stepwise, {"cwd": stepwise, "session_id": "k3"})

        # Revue par modele en echec : le rapport le dit au lieu d'annoncer un verdict complet.
        reviewed = sandbox.make_repo("reviewed", {"b.py": CLEAN})
        Sandbox.write(sandbox.config_dir, "supervisor.config.json",
                      json.dumps({"llm": {"enabled": True, "cli": _failing_reviewer(sandbox), "timeout_seconds": 30}}))
        no_llm = {key: value for key, value in sandbox.env.items() if key != "SUPERVISOR_NO_LLM"}
        sandbox.env, previous_env = no_llm, sandbox.env
        try:
            results["llm_review_failed"] = sandbox.run(reviewed, {"cwd": reviewed, "session_id": "l1"})
        finally:
            sandbox.env = previous_env
            os.remove(os.path.join(sandbox.config_dir, "supervisor.config.json"))

        logs = os.path.join(sandbox.work, "logs")
        os.makedirs(logs)
        Sandbox.write(logs, "state-s9.json", "{corrompu")
        results["state_corrupt"] = sandbox.run(bad, dict(payload, session_id="s9"), {"SUPERVISOR_LOG_DIR": logs})
        results["log_dir_files"] = sorted(sandbox.normalize(n) for n in os.listdir(logs))
        with open(os.path.join(logs, ".gitignore"), encoding="utf-8") as fh:
            results["log_gitignore"] = fh.read()

        accented = sandbox.make_repo("dépôt", {"a.py": BAD})
        raw = json.dumps({"cwd": accented, "session_id": "u1"}, ensure_ascii=False)
        results["accented_path"] = sandbox.run(accented, raw=raw)

        results["cli_check_bad"] = sandbox.run(bad, args=["--check", "a.py"], raw="")
        results["cli_check_clean"] = sandbox.run(clean, args=["--check", "b.py"], raw="")
        results["cli_check_diff"] = sandbox.run(bad, args=["--check"], raw="")
        results["self_test"] = sandbox.run(bad, args=["--self-test"], raw="")
        results["states"] = _states(bad)
    finally:
        sandbox.close()
    return results
