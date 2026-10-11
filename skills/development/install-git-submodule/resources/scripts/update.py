#!/usr/bin/env python3
"""Met à jour les sous-modules gérés d'un dépôt consommateur.

Pour chaque sous-module géré : récupère la branche suivie, avance la référence si elle a changé,
lance les contrôles du dépôt, crée un commit limité à cette référence, puis pousse. Rien n'est
commité quand le commit référencé n'a pas changé.

Le dépôt source reste la source de vérité, mais ce script ne lui obéit pas aveuglément : c'est
toujours la tête de la branche déclarée dans `.gitmodules` qui est adoptée, jamais le SHA annoncé
par un événement ; un retour en arrière est refusé ; un sous-module modifié sur le poste n'est
jamais écrasé ; les contrôles sont ceux de ce dépôt, lancés sans aucun jeton dans l'environnement.

Commandes :
  run      met à jour (c'est ce que lance la CI) ; `--push` pour pousser
  status   compare chaque référence à la tête de sa branche, sans rien écrire

Bibliothèque standard, Python 3.8+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Le module commun est à côté du script dans un dépôt (.github/submodule-sync/), et dans le dossier
# voisin `git-submodule-common` quand le script tourne depuis le skill installé.
SHARED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "git-submodule-common",
                      "resources", "scripts")
sys.path[:0] = [HERE, SHARED]
try:
    import submodule_common as common
except ImportError:
    sys.exit("module commun introuvable : installer `git-submodule-common` à côté de ce skill "
             "(python tools/install_skill.py install git-submodule-common)")
SyncError, git, git_out, log, warn = common.SyncError, common.git, common.git_out, common.log, common.warn

CONFIG_PATH = ".github/submodule-update.json"
WORKFLOW_PATH = ".github/workflows/submodule-update.yml"
DOC_PATH = common.SYNC_DIR + "/UPDATE.md"
SCRIPT_FILES = ("update.py", "submodule_common.py")
DEFAULT_SCHEDULE = "17 */6 * * *"
PAYLOAD_ENV = "SUBMODULE_EVENT_PAYLOAD"
ONLY_PATH_ENV = "SUBMODULE_ONLY_PATH"
PAYLOAD_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
PR_PREFIX = "submodule-update/"


# --------------------------------------------------------------------------- configuration

def _checks(value, where: str) -> list:
    value = value or []
    if not isinstance(value, list) or any(not isinstance(c, str) or not c.strip() for c in value):
        raise SyncError("%s : `checks` doit être une liste de commandes" % where, common.EXIT_USAGE)
    return list(value)


def normalize_config(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("submodules", []), list):
        raise SyncError("%s : objet avec une liste `submodules` attendu" % CONFIG_PATH, common.EXIT_USAGE)
    mode = data.get("mode") or "push"
    if mode not in ("push", "pr"):
        raise SyncError("%s : `mode` vaut push ou pr, pas %r" % (CONFIG_PATH, mode), common.EXIT_USAGE)
    schedule = data.get("schedule", DEFAULT_SCHEDULE)
    target = data.get("target_branch")
    entries, seen = [], set()
    for item in data.get("submodules", []):
        if not isinstance(item, dict):
            raise SyncError("%s : entrée de sous-module mal formée" % CONFIG_PATH, common.EXIT_USAGE)
        path = common.validate_rel_path(item.get("path"), "chemin de sous-module")
        if path in seen:
            raise SyncError("%s : %r est déclaré deux fois" % (CONFIG_PATH, path), common.EXIT_USAGE)
        seen.add(path)
        entries.append({
            "path": path,
            "checks": _checks(item.get("checks"), path),
            "hold": common.parse_bool(item.get("hold", False)),
            "allow_non_fast_forward": common.parse_bool(item.get("allow_non_fast_forward", False)),
        })
    return {
        "version": 1,
        "remote": common.validate_remote(data.get("remote") or "origin"),
        "target_branch": common.validate_branch(target, "branche destinataire") if target else None,
        "mode": mode,
        "schedule": common.validate_cron(schedule) if schedule else None,
        "checks": _checks(data.get("checks"), CONFIG_PATH),
        "submodules": sorted(entries, key=lambda e: e["path"]),
    }


def load_config(root: str) -> dict:
    path = os.path.join(root, CONFIG_PATH)
    if not os.path.isfile(path):
        return normalize_config({"submodules": []})
    return normalize_config(common.load_json(path))


def read_gitmodules(root: str) -> dict:
    """`.gitmodules` indexé par chemin : {chemin: {name, url, branch}}."""
    if not os.path.isfile(os.path.join(root, ".gitmodules")):
        return {}
    proc = git(["config", "-f", ".gitmodules", "-z", "--get-regexp", r"^submodule\..*\.(path|url|branch)$"],
               cwd=root, check=False)
    by_name = {}
    for item in proc.stdout.split("\0"):
        key, _, value = item.partition("\n")
        match = re.match(r"^submodule\.(.*)\.(path|url|branch)$", key, re.S)
        if match:
            by_name.setdefault(match.group(1), {"name": match.group(1)})[match.group(2)] = value
    return {m["path"]: m for m in by_name.values() if m.get("path") and m.get("url")}


def gitlink(root: str, path: str):
    """SHA enregistré pour le sous-module dans HEAD, ou None si ce n'en est pas un."""
    entry = git(["ls-tree", "HEAD", "--", path], cwd=root, check=False).stdout.strip()
    parts = entry.split()
    return parts[2] if len(parts) >= 3 and parts[0] == "160000" else None


# --------------------------------------------------------------------------- événement

def read_payload():
    """Charge utile d'un `repository_dispatch`, validée champ par champ. None hors événement."""
    raw = os.environ.get(PAYLOAD_ENV, "").strip()
    if raw in ("", "null", "{}"):
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        raise SyncError("charge utile de l'événement illisible : rien n'est fait", common.EXIT_USAGE)
    if not isinstance(data, dict):
        raise SyncError("charge utile de l'événement mal formée : rien n'est fait", common.EXIT_USAGE)
    repo, branch, sha = data.get("source_repo"), data.get("branch"), data.get("sha")
    source_sha = data.get("source_sha")
    if (not isinstance(repo, str) or not common.SLUG_RE.match(repo)
            or not isinstance(branch, str) or not PAYLOAD_BRANCH_RE.match(branch)
            or not isinstance(sha, str) or not common.SHA_RE.match(sha)
            or (source_sha is not None and not (isinstance(source_sha, str) and common.SHA_RE.match(source_sha)))):
        raise SyncError("charge utile de l'événement invalide (source_repo, branch ou sha) : rien n'est fait",
                        common.EXIT_USAGE)
    return {"source_repo": repo, "branch": branch, "sha": sha, "source_sha": source_sha}


def matches_payload(module: dict, payload: dict) -> bool:
    slug = common.url_slug(module["url"])
    return bool(slug) and slug.lower() == payload["source_repo"].lower() and module.get("branch") == payload["branch"]


# --------------------------------------------------------------------------- mise à jour

def run_checks(root: str, commands, result: dict):
    """Lance les contrôles du dépôt. Retourne la première commande en échec, ou None."""
    env = common.clean_env()
    env.update(SUBMODULE_PATH=result["path"], SUBMODULE_OLD_SHA=result["old"], SUBMODULE_NEW_SHA=result["new"])
    for command in commands:
        log("  contrôle : %s" % command)
        # Commande écrite par ce dépôt dans sa propre configuration : le shell est voulu.
        proc = subprocess.run(command, shell=True, cwd=root, env=env)
        if proc.returncode != 0:
            return "%s (code %d)" % (command, proc.returncode)
    return None


def update_one(root: str, cfg: dict, entry: dict, module: dict, payload, fetch_env: dict) -> dict:
    path, branch = entry["path"], module.get("branch")
    result = {"path": path, "url": module["url"], "branch": branch, "old": None, "new": None,
              "source_sha": None, "status": None}
    if entry["hold"]:
        result["status"] = "held"
        return result
    if not branch:
        raise SyncError("%s : `.gitmodules` ne déclare aucune branche à suivre" % path, common.EXIT_USAGE)
    common.validate_branch(branch, "branche suivie")
    common.validate_url(module["url"])
    old = gitlink(root, path)
    if not old:
        raise SyncError("%s n'est pas un sous-module dans HEAD" % path, common.EXIT_USAGE)
    result["old"] = old
    if git(["diff", "--cached", "--quiet", "--", path], cwd=root, check=False).returncode != 0:
        raise SyncError("%s : la référence est déjà modifiée dans l'index (travail en cours) : rien "
                        "n'est touché" % path, common.EXIT_DECISION)
    sub = os.path.join(root, path)
    if not os.path.exists(os.path.join(sub, ".git")):
        proc = git(["submodule", "update", "--init", "--", path], cwd=root, env=fetch_env, check=False)
        if proc.returncode != 0:
            raise SyncError("%s : initialisation impossible (accès à %s ?) : %s"
                            % (path, module["url"], proc.stderr.strip()), common.EXIT_ACCESS)
    else:
        # Le producteur fait foi, mais jamais au prix d'un travail local.
        if git_out(["rev-parse", "HEAD"], cwd=sub) != old:
            raise SyncError("%s : le sous-module est sur un autre commit que celui enregistré (travail "
                            "local ?) : rien n'est écrasé" % path, common.EXIT_DECISION)
        if git(["status", "--porcelain", "--untracked-files=no"], cwd=sub).stdout.strip():
            raise SyncError("%s : fichiers modifiés dans le sous-module : rien n'est écrasé" % path,
                            common.EXIT_DECISION)
    ref = "refs/remotes/origin/" + branch
    proc = git(["fetch", "--no-tags", "origin", "+refs/heads/%s:%s" % (branch, ref)], cwd=sub,
               env=fetch_env, check=False)
    if proc.returncode != 0:
        raise SyncError("%s : branche %s inaccessible sur %s : %s"
                        % (path, branch, module["url"], proc.stderr.strip()), common.EXIT_ACCESS)
    new = git_out(["rev-parse", ref + "^{commit}"], cwd=sub)
    result["new"] = new
    if payload and payload["sha"] != new:
        log("  %s : l'événement annonçait %s, la branche est à %s — c'est la branche qui fait foi"
            % (path, payload["sha"][:12], new[:12]))
    if new == old:
        result["status"] = "unchanged"
        return result
    if not common.is_ancestor(sub, old, new) and not entry["allow_non_fast_forward"]:
        raise SyncError(
            "%s : %s n'est pas un descendant de la référence actuelle %s. La branche %s a été réécrite, "
            "ou la référence a été épinglée hors de cette branche. Aucun retour en arrière automatique : "
            "vérifier, puis poser `allow_non_fast_forward` (ou `hold`) sur ce sous-module dans %s."
            % (path, new[:12], old[:12], branch, CONFIG_PATH), common.EXIT_DIVERGED)
    git(["checkout", "-q", "--detach", new], cwd=sub)
    git(["add", "--", path], cwd=root)
    failed = run_checks(root, cfg["checks"] + entry["checks"], result)
    if failed:
        git(["checkout", "-q", "--detach", old], cwd=sub)
        git(["reset", "-q", "HEAD", "--", path], cwd=root)
        raise SyncError("%s : contrôle échoué — %s. La référence reste à %s, rien n'est publié."
                        % (path, failed, old[:12]), common.EXIT_ERROR)
    trailers = ["Submodule-Path: " + path, "Submodule-Url: " + module["url"], "Submodule-Branch: " + branch,
                "Submodule-Old: " + old, "Submodule-New: " + new]
    if payload and payload["sha"] == new and payload["source_sha"]:
        result["source_sha"] = payload["source_sha"]
        trailers.append("Source-Commit: " + payload["source_sha"])
    message = "chore(submodule): %s -> %s\n\n%s\n" % (path, new[:12], "\n".join(trailers))
    git(["commit", "-q", "-m", message, "--", path], cwd=root, env=common.identity_env(root))
    result["status"] = "updated"
    return result


def push_token() -> str:
    return (os.environ.get("SUBMODULE_PUSH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()


def push_direct(root: str, cfg: dict) -> None:
    """Pousse sans jamais forcer. Sur rejet, rebase le ou les commits de référence et réessaie."""
    env = common.auth_env(push_token())
    remote, target = cfg["remote"], cfg["target_branch"]
    stderr = ""
    for _ in range(3):
        proc = git(["push", remote, "HEAD:refs/heads/" + target], cwd=root, env=env, check=False)
        if proc.returncode == 0:
            return
        stderr = proc.stderr.strip()
        if git(["fetch", "--no-tags", remote, "refs/heads/" + target], cwd=root, env=env, check=False).returncode != 0:
            break
        if git(["rebase", "FETCH_HEAD"], cwd=root, env=common.identity_env(root), check=False).returncode != 0:
            git(["rebase", "--abort"], cwd=root, check=False)
            raise SyncError("push refusé, et le rebase sur %s est impossible (la même référence a changé "
                            "entre-temps, ou un contrôle a modifié des fichiers suivis) : rien n'est forcé. "
                            "La prochaine exécution repartira de l'état distant." % target, common.EXIT_PUSH)
    raise SyncError("push vers %s refusé : %s. Si la branche est protégée, passer `mode` à `pr` dans %s "
                    "(voir references/permissions.md) ; aucune protection n'est contournée."
                    % (target, stderr, CONFIG_PATH), common.EXIT_PUSH)


def gh(root: str, args, check=True):
    try:
        prefix = json.loads(os.environ.get("SUBMODULE_SYNC_GH") or '["gh"]')
    except ValueError:
        prefix = ["gh"]
    env = dict(os.environ)
    env["GH_TOKEN"] = push_token() or env.get("GH_TOKEN", "")
    if os.environ.get("GITHUB_REPOSITORY"):
        env["GH_REPO"] = os.environ["GITHUB_REPOSITORY"]
    try:
        proc = subprocess.run(list(prefix) + list(args), cwd=root, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SyncError("GitHub CLI (`gh`) indisponible : %s — il est requis par `mode: pr`" % exc)
    if check and proc.returncode != 0:
        raise SyncError("gh %s a échoué : %s" % (" ".join(args[:2]), proc.stderr.strip()), common.EXIT_PUSH)
    return proc


def push_pull_request(root: str, cfg: dict, updated: list, complete: bool) -> str:
    """Branche protégée : pull request avec fusion automatique, soumise aux contrôles obligatoires."""
    target = cfg["target_branch"]
    digest = hashlib.sha256("".join(r["path"] + r["new"] for r in updated).encode("utf-8")).hexdigest()[:10]
    prefix = PR_PREFIX + common.slugify(target) + "-"
    head = prefix + digest
    env = common.auth_env(push_token())
    # Le nom de la branche encode les SHA adoptés : si elle existe déjà, une exécution précédente
    # l'a poussée et sa pull request attend. La repousser serait rejeté (même contenu, autre commit).
    if not git(["ls-remote", "--heads", cfg["remote"], "refs/heads/" + head], cwd=root, env=env,
               check=False).stdout.strip():
        proc = git(["push", cfg["remote"], "HEAD:refs/heads/" + head], cwd=root, env=env, check=False)
        if proc.returncode != 0:
            raise SyncError("push de la branche %s refusé : %s" % (head, proc.stderr.strip()), common.EXIT_PUSH)
    listing = json.loads(gh(root, ["pr", "list", "--state", "open", "--base", target,
                                   "--json", "number,headRefName"]).stdout or "[]")
    if not any(pr.get("headRefName") == head for pr in listing):
        title = "chore(submodule): " + ", ".join("%s -> %s" % (r["path"], r["new"][:12]) for r in updated)
        body = "\n".join("- `%s` (`%s`) : `%s` -> `%s`" % (r["path"], r["branch"], r["old"], r["new"])
                         for r in updated)
        gh(root, ["pr", "create", "--base", target, "--head", head, "--title", title,
                  "--body", "Mise à jour automatique des sous-modules.\n\n" + body])
    merge = gh(root, ["pr", "merge", head, "--auto", "--squash"], check=False)
    if merge.returncode != 0:
        raise SyncError(
            "pull request ouverte sur %s, mais la fusion automatique n'a pas pu être activée : %s. "
            "Activer « Allow auto-merge » dans les réglages du dépôt ; si une revue humaine est "
            "obligatoire, la mise à jour ne peut pas être entièrement automatique."
            % (head, merge.stderr.strip()), common.EXIT_PUSH)
    # Une exécution partielle (événement, chemin demandé) ne juge pas des autres sous-modules.
    for pr in listing if complete else []:
        name = pr.get("headRefName", "")
        if name.startswith(prefix) and name != head:
            gh(root, ["pr", "close", str(pr["number"]), "--delete-branch",
                      "--comment", "Remplacée par une mise à jour plus récente (%s)." % head], check=False)
    return head


def select_entries(cfg: dict, modules: dict, payload, only):
    entries = cfg["submodules"]
    if only:
        entries = [e for e in entries if e["path"] == only]
        if not entries:
            raise SyncError("%r n'est pas un sous-module géré (%s)" % (only, CONFIG_PATH), common.EXIT_USAGE)
    for entry in entries:
        if entry["path"] not in modules:
            raise SyncError("%s est géré dans %s mais absent de .gitmodules" % (entry["path"], CONFIG_PATH),
                            common.EXIT_USAGE)
    if payload:
        entries = [e for e in entries if matches_payload(modules[e["path"]], payload)]
    return entries


def cmd_run(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    modules = read_gitmodules(root)
    payload = read_payload()
    only = args.path or os.environ.get(ONLY_PATH_ENV, "").strip() or None
    if only:
        only = common.validate_rel_path(only, "chemin demandé")
    entries = select_entries(cfg, modules, payload, only)
    if payload and not entries:
        warn("événement ignoré : aucun sous-module géré ne suit %s@%s" % (payload["source_repo"], payload["branch"]))
        return common.EXIT_OK
    if not entries:
        log("Aucun sous-module géré dans %s." % CONFIG_PATH)
        return common.EXIT_OK
    if args.push:
        if not cfg["target_branch"]:
            raise SyncError("%s : `target_branch` absent" % CONFIG_PATH, common.EXIT_USAGE)
        if common.current_branch(root) != cfg["target_branch"]:
            raise SyncError("la branche courante n'est pas la branche destinataire %s : rien n'est poussé "
                            "depuis une autre branche" % cfg["target_branch"], common.EXIT_USAGE)

    fetch_env = common.auth_env((os.environ.get("SUBMODULE_FETCH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip())
    code, results = common.EXIT_OK, []
    for entry in entries:
        try:
            result = update_one(root, cfg, entry, modules[entry["path"]], payload, fetch_env)
        except SyncError as exc:
            common.error(str(exc))
            code = code or exc.code
            result = {"path": entry["path"], "branch": modules[entry["path"]].get("branch"), "old": None,
                      "new": None, "source_sha": None, "status": "failed", "error": str(exc)}
        results.append(result)
        log("%s : %s%s" % (result["path"], result["status"],
                           " (%s -> %s)" % (result["old"][:12], result["new"][:12]) if result["status"] == "updated" else ""))

    updated = [r for r in results if r["status"] == "updated"]
    pushed = None
    if updated and args.push:
        try:
            if cfg["mode"] == "pr":
                pushed = "pull request " + push_pull_request(root, cfg, updated, not payload and not only)
            else:
                push_direct(root, cfg)
                pushed = cfg["target_branch"]
            log("Poussé : %s" % pushed)
        except SyncError as exc:
            common.error(str(exc))
            code = code or exc.code
    elif updated:
        log("Commit(s) créé(s) localement, non poussé(s) (ajouter --push).")

    rows = ["| `%s` | `%s` | `%s` | `%s` | `%s` | %s |" % (
        r["path"], r.get("branch") or "", (r["old"] or "")[:12], (r["new"] or "")[:12],
        (r.get("source_sha") or "")[:12], r["status"]) for r in results]
    common.step_summary("### Mise à jour des sous-modules\n\n| Chemin | Branche | Ancien | Nouveau | Source | État |\n"
                        "|---|---|---|---|---|---|\n" + "\n".join(rows))
    if args.json:
        log(json.dumps({"results": results, "pushed": pushed}, ensure_ascii=False, indent=2))
    return code


def cmd_status(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    modules = read_gitmodules(root)
    env = common.auth_env((os.environ.get("SUBMODULE_FETCH_TOKEN") or "").strip())
    code = common.EXIT_OK
    for entry in select_entries(cfg, modules, None, None):
        module = modules[entry["path"]]
        proc = git(["ls-remote", "--heads", "--", module["url"], "refs/heads/%s" % module.get("branch")],
                   cwd=root, env=env, check=False)
        tip = proc.stdout.split("\t")[0].strip() if proc.returncode == 0 else ""
        recorded = gitlink(root, entry["path"]) or ""
        if not tip:
            state, code = "branche inaccessible", code or common.EXIT_ACCESS
        else:
            state = "à jour" if tip == recorded else "en retard"
        log("%s : %s@%s — enregistré %s, branche %s — %s%s" % (
            entry["path"], module["url"], module.get("branch"), recorded[:12], tip[:12] or "?", state,
            " (suspendu)" if entry["hold"] else ""))
    if not cfg["submodules"]:
        log("Aucun sous-module géré dans %s." % CONFIG_PATH)
    return code


def build_parser() -> argparse.ArgumentParser:
    flag = dict(nargs="?", const=True, default=False, type=common.parse_bool)
    parser = argparse.ArgumentParser(description="Mise à jour des sous-modules gérés.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="mettre à jour les sous-modules gérés")
    run.add_argument("--path", help="un seul sous-module (défaut : tous)")
    run.add_argument("--push", **flag)
    run.add_argument("--json", action="store_true")
    run.set_defaults(func=cmd_run)
    sub.add_parser("status").set_defaults(func=cmd_status)
    return parser


def main(argv) -> int:
    args = build_parser().parse_args(common.kv_to_argv(argv, {"path", "push"}))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(common.run_main(main))
