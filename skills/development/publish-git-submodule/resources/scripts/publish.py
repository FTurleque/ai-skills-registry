#!/usr/bin/env python3
"""Publie un dépôt, ou un dossier d'un dépôt, comme source de sous-module.

Deux modes, décidés par `source` :
  - dépôt entier (`source=.`) : rien n'est extrait, la branche source est la branche à suivre ;
  - dossier (`source=.claude`) : le contenu du dossier est publié à la racine d'une branche
    d'export du même dépôt distant, par `git subtree split` (ou par instantané, voir `strategy`).

Commandes :
  setup       prépare une publication : contrôles, publication initiale, configuration, workflow
  run         publie les exports configurés et notifie les consommateurs (c'est ce que lance la CI)
  register    inscrit un dépôt consommateur à notifier ; `unregister` le retire
  status      compare chaque export à sa source, sans rien écrire
  render      régénère le workflow à partir de la configuration

Les paramètres s'écrivent `--clé valeur` ou `clé=valeur`. Bibliothèque standard, Python 3.8+.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import submodule_common as common
from submodule_common import SyncError, git, git_out, log, warn

CONFIG_PATH = ".github/submodule-publish.json"
WORKFLOW_PATH = ".github/workflows/submodule-publish.yml"
DOC_PATH = common.SYNC_DIR + "/PUBLISH.md"
SCRIPT_FILES = ("publish.py", "submodule_common.py")
DISPATCH_TOKEN_ENV = "SUBMODULE_DISPATCH_TOKEN"
MAX_SCAN_BYTES = 1000000
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
KV_KEYS = {"source", "branch", "export", "name", "remote", "strategy", "exclude", "auto", "consumer",
           "accept-findings", "dry-run", "no-publish", "commit", "push", "force", "allow-force"}

# Fichiers dont le seul nom signale un contenu local ou secret.
NAME_RULES = [
    ("local-settings", ["settings.local.json", "*.local.json", "*.local.md", "*.local.yaml", "*.local.yml"]),
    ("env-file", [".env", ".env.*"]),
    ("key-file", ["*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"]),
    ("credentials-file", [".credentials.json", "credentials.json", ".netrc", ".git-credentials"]),
]
ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template", ".env.dist"}
SECRET_RULES = [
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
]
# Répertoire personnel d'un poste : la chaîne est assemblée pour ne pas être prise elle-même
# pour un chemin local par les contrôles d'hygiène.
PERSONAL_PATH = re.compile("(?:[A-Za-z]:[\\\\/]{1,2}Users[\\\\/]{1,2}|/" + "home/|/" + "Users/)([A-Za-z0-9._-]+)")
GENERIC_USERS = {"user", "username", "you", "name", "xxx", "public", "shared", "default", "runner",
                 "runneradmin"}


# --------------------------------------------------------------------------- configuration

def normalize_publication(pub: dict) -> dict:
    """Valide une publication. La configuration est une entrée : elle est revérifiée à chaque exécution."""
    if not isinstance(pub, dict):
        raise SyncError("publication mal formée dans %s" % CONFIG_PATH, common.EXIT_USAGE)
    name = pub.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise SyncError("nom de publication invalide : %r (minuscules, chiffres, tirets)" % (name,),
                        common.EXIT_USAGE)
    source = common.validate_rel_path(pub.get("source"), "source", allow_root=True)
    branch = common.validate_branch(pub.get("branch"), "branche source")
    whole = source == "."
    export = pub.get("export")
    if whole:
        export = None
    else:
        export = common.validate_branch(export, "branche d'export")
        if export == branch:
            raise SyncError("la branche d'export doit différer de la branche source (%s)" % branch,
                            common.EXIT_USAGE)
    strategy = pub.get("strategy") or "subtree"
    if strategy not in ("subtree", "snapshot"):
        raise SyncError("stratégie inconnue : %r (subtree ou snapshot)" % (strategy,), common.EXIT_USAGE)
    exclude = pub.get("exclude") or []
    if not isinstance(exclude, list) or any(not isinstance(p, str) or not p.strip() for p in exclude):
        raise SyncError("`exclude` doit être une liste de motifs", common.EXIT_USAGE)
    for pattern in exclude:
        if pattern.startswith(("/", "-")) or ".." in pattern.split("/") or "\\" in pattern:
            raise SyncError("motif d'exclusion refusé : %r" % pattern, common.EXIT_USAGE)
    if exclude and (whole or strategy != "snapshot"):
        raise SyncError(
            "`exclude` n'existe qu'avec `strategy=snapshot` sur un dossier : `git subtree split` "
            "extrait un dossier avec son historique, ce n'est pas un filtre de fichiers. Voir "
            "references/security-and-history.md.", common.EXIT_USAGE)
    consumers = pub.get("consumers") or []
    accepted = pub.get("accepted_findings") or []
    if not isinstance(consumers, list) or not isinstance(accepted, list):
        raise SyncError("`consumers` et `accepted_findings` doivent être des listes", common.EXIT_USAGE)
    if any(not isinstance(f, str) or not re.match(r"^[0-9a-f]{16}$", f) for f in accepted):
        raise SyncError("`accepted_findings` contient une empreinte invalide", common.EXIT_USAGE)
    return {
        "name": name,
        "source": source,
        "branch": branch,
        "export": export,
        "remote": common.validate_remote(pub.get("remote") or "origin"),
        "strategy": strategy,
        "exclude": sorted(set(exclude)),
        "auto": common.parse_bool(pub.get("auto", True)),
        "allow_force": common.parse_bool(pub.get("allow_force", False)),
        "consumers": sorted({common.validate_slug(c, "consommateur") for c in consumers}, key=str.lower),
        "accepted_findings": sorted(set(accepted)),
    }


def load_config(root: str) -> dict:
    path = os.path.join(root, CONFIG_PATH)
    if not os.path.isfile(path):
        return {"version": 1, "publications": []}
    data = common.load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("publications"), list):
        raise SyncError("%s : objet avec une liste `publications` attendu" % CONFIG_PATH, common.EXIT_USAGE)
    pubs = [normalize_publication(p) for p in data["publications"]]
    names = [p["name"] for p in pubs]
    exports = [p["export"] for p in pubs if p["export"]]
    if len(set(names)) != len(names) or len(set(exports)) != len(exports):
        raise SyncError("%s : deux publications partagent un nom ou une branche d'export" % CONFIG_PATH,
                        common.EXIT_USAGE)
    if set(exports) & {p["branch"] for p in pubs}:
        raise SyncError("%s : une branche d'export est aussi la branche source d'une publication"
                        % CONFIG_PATH, common.EXIT_USAGE)
    return {"version": 1, "publications": pubs}


def save_config(root: str, cfg: dict) -> bool:
    cfg["publications"].sort(key=lambda p: p["name"])
    return common.dump_json(os.path.join(root, CONFIG_PATH), cfg)


def find_publication(cfg: dict, name: str):
    for pub in cfg["publications"]:
        if pub["name"] == name:
            return pub
    return None


def require_publication(cfg: dict, name: str) -> dict:
    pub = find_publication(cfg, name)
    if pub is None:
        known = ", ".join(p["name"] for p in cfg["publications"]) or "aucune"
        raise SyncError("publication inconnue : %r (configurées : %s)" % (name, known), common.EXIT_USAGE)
    return pub


# --------------------------------------------------------------------------- remote

def remote_url(root: str, remote: str) -> str:
    proc = git(["remote", "get-url", remote], cwd=root, check=False)
    if proc.returncode != 0:
        raise SyncError("remote %r absent de ce dépôt" % remote, common.EXIT_ACCESS)
    # Jamais d'identifiant recopié dans un rapport ou une commande suggérée.
    return re.sub(r"^(https?://)[^/@]+@", r"\1", proc.stdout.strip())


def remote_heads(root: str, remote: str) -> dict:
    proc = git(["ls-remote", "--heads", remote], cwd=root, check=False)
    if proc.returncode != 0:
        raise SyncError("remote %r inaccessible : %s" % (remote, proc.stderr.strip()), common.EXIT_ACCESS)
    heads = {}
    for line in proc.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            heads[ref[len("refs/heads/"):]] = sha
    return heads


def fetch_branch(root: str, remote: str, branch: str) -> str:
    """Met à jour la référence distante de la branche source et retourne son commit."""
    if git_out(["rev-parse", "--is-shallow-repository"], cwd=root) == "true":
        # Une extraction a besoin de tout l'historique du dossier.
        git(["fetch", "--no-tags", "--unshallow", remote], cwd=root)
    ref = "refs/remotes/%s/%s" % (remote, branch)
    proc = git(["fetch", "--no-tags", remote, "+refs/heads/%s:%s" % (branch, ref)], cwd=root, check=False)
    if proc.returncode != 0:
        raise SyncError("branche source %r introuvable ou inaccessible sur %r : %s"
                        % (branch, remote, proc.stderr.strip()), common.EXIT_ACCESS)
    return git_out(["rev-parse", ref + "^{commit}"], cwd=root)


# --------------------------------------------------------------------------- extraction

def check_source_tree(root: str, commit: str, source: str) -> int:
    """Vérifie que le dossier existe dans le commit, n'est pas un sous-module et contient des fichiers."""
    entry = git(["ls-tree", commit, "--", source], cwd=root).stdout.strip()
    if not entry:
        raise SyncError(
            "le dossier %r n'existe pas dans le commit source %s (supprimé ou jamais suivi). "
            "L'export existant est laissé tel quel : restaurer le dossier, ou retirer la publication."
            % (source, commit[:12]), common.EXIT_USAGE)
    mode = entry.split()[0]
    if mode == "160000":
        raise SyncError(
            "%r est déjà un sous-module de ce dépôt : il n'y a rien à extraire. Les consommateurs "
            "installent directement le dépôt qu'il référence (voir `git config -f .gitmodules -l`)."
            % source, common.EXIT_USAGE)
    if mode != "040000":
        raise SyncError("%r n'est pas un dossier dans le commit source" % source, common.EXIT_USAGE)
    files = 0
    for line in git(["ls-tree", "-r", "-z", commit, "--", source + "/"], cwd=root).stdout.split("\0"):
        if not line:
            continue
        if line.split(" ", 1)[0] == "160000":
            raise SyncError(
                "%r contient lui-même un sous-module (%s) : son .gitmodules reste à la racine du dépôt "
                "source et ne serait pas exporté. Publier ce sous-module à part."
                % (source, line.split("\t", 1)[-1]), common.EXIT_USAGE)
        files += 1
    if files == 0:
        raise SyncError("%r ne contient aucun fichier suivi : rien à publier" % source, common.EXIT_USAGE)
    return files


def subtree_split(root: str, commit: str, prefix: str) -> str:
    """`git subtree split` sur le commit source, sans toucher à l'arbre de travail de l'utilisateur."""
    probe = git(["subtree", "-h"], cwd=root, check=False)
    if "is not a git command" in (probe.stderr + probe.stdout):
        raise SyncError("`git subtree` est absent de cette installation de git (paquet git-subtree, "
                        "ou contrib/subtree) : il est requis pour `strategy=subtree`.", common.EXIT_USAGE)

    def split(cwd: str) -> str:
        out = git(["subtree", "split", "-q", "--prefix=" + prefix], cwd=cwd).stdout.strip().splitlines()
        sha = out[-1].strip() if out else ""
        if not common.SHA_RE.match(sha):
            raise SyncError("`git subtree split` n'a retourné aucun commit pour %r" % prefix)
        return sha

    head = git(["rev-parse", "-q", "--verify", "HEAD"], cwd=root, check=False).stdout.strip()
    if head == commit and os.path.isdir(os.path.join(root, prefix)):
        return split(root)
    tmp = tempfile.mkdtemp(prefix="submodule-publish-")
    try:
        git(["worktree", "add", "-q", "--detach", tmp, commit], cwd=root)
        return split(tmp)
    finally:
        git(["worktree", "remove", "--force", tmp], cwd=root, check=False)
        common.force_rmtree(tmp)
        git(["worktree", "prune"], cwd=root, check=False)


def matches_exclude(path: str, patterns) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif "/" in pattern:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        elif fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], pattern):
            return True
    return False


def snapshot_commit(root: str, commit: str, prefix: str, excludes, parent):
    """Commit d'export sans l'historique de la source : l'arbre du dossier, moins les exclusions.

    Retourne `parent` quand l'arbre est déjà celui de l'export : aucun commit inutile.
    """
    tree = git_out(["rev-parse", "%s:%s" % (commit, prefix)], cwd=root)
    if excludes:
        handle, index = tempfile.mkstemp(prefix="submodule-index-")
        os.close(handle)
        os.unlink(index)
        env = dict(os.environ, GIT_INDEX_FILE=index)
        try:
            git(["read-tree", tree], cwd=root, env=env)
            names = [n for n in git(["ls-files", "-z"], cwd=root, env=env).stdout.split("\0") if n]
            drop = [n for n in names if matches_exclude(n, excludes)]
            if drop:
                git(["update-index", "--force-remove", "-z", "--stdin"], cwd=root, env=env,
                    input_text="\0".join(drop) + "\0")
            tree = git_out(["write-tree"], cwd=root, env=env)
        finally:
            if os.path.exists(index):
                os.unlink(index)
    if not git(["ls-tree", tree], cwd=root).stdout.strip():
        raise SyncError("après exclusions, %r ne contient plus aucun fichier : rien à publier" % prefix,
                        common.EXIT_USAGE)
    if parent and git_out(["rev-parse", parent + "^{tree}"], cwd=root) == tree:
        return parent
    name, email, date = git_out(["show", "-s", "--format=%an%n%ae%n%aI", commit], cwd=root).split("\n")[:3]
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=date,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email, GIT_COMMITTER_DATE=date)
    message = "Export de %s (%s)\n\nSource-Commit: %s\nSource-Path: %s\n" % (prefix, commit[:12], commit, prefix)
    args = ["commit-tree", tree] + (["-p", parent] if parent else []) + ["-m", message]
    return git_out(args, cwd=root, env=env)


# --------------------------------------------------------------------------- contenu sensible

def fingerprint(rule: str, path: str, match: str = "") -> str:
    return hashlib.sha256(("%s\0%s\0%s" % (rule, path, match)).encode("utf-8")).hexdigest()[:16]


def name_rule(path: str):
    base = path.rsplit("/", 1)[-1]
    if base in ENV_EXAMPLES:
        return None
    for rule, patterns in NAME_RULES:
        if any(fnmatch.fnmatchcase(base, p) for p in patterns):
            return rule
    return None


def read_blobs(root: str, shas):
    """Retourne (ensemble des blobs, contenu de ceux de taille raisonnable), en deux processus git."""
    if not shas:
        return set(), {}
    feed = ("\n".join(shas) + "\n").encode("ascii")
    check = subprocess.run(["git", "cat-file", "--batch-check"], cwd=root, input=feed,
                           stdout=subprocess.PIPE, check=True).stdout.decode("ascii", "replace")
    wanted, known = [], set()
    for line in check.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "blob":
            known.add(parts[0])
            if int(parts[2]) <= MAX_SCAN_BYTES:
                wanted.append(parts[0])
    if not wanted:
        return known, {}
    data = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
                          input=("\n".join(wanted) + "\n").encode("ascii"),
                          stdout=subprocess.PIPE, check=True).stdout
    blobs, pos = {}, 0
    for sha in wanted:
        end = data.index(b"\n", pos)
        size = int(data[pos:end].split()[2])
        blobs[sha] = data[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
    return known, blobs


def scan(root: str, new: str, base=None):
    """Cherche fichiers locaux, secrets et chemins personnels dans ce qui va être publié.

    Tout l'historique publié est lu, pas seulement le dernier commit : un fichier supprimé depuis
    reste téléchargeable par quiconque clone la branche d'export. Avec `base`, seuls les objets
    absents de l'export déjà publié sont lus.
    """
    tip = {}
    for entry in git(["ls-tree", "-r", "-z", new], cwd=root).stdout.split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            tip[path] = meta.split(" ")[2]
    objects = []
    for line in git(["rev-list", "--objects", new] + (["^" + base] if base else []), cwd=root).stdout.splitlines():
        sha, _, path = line.partition(" ")
        if path:
            objects.append((sha, path))
    known, blobs = read_blobs(root, sorted({sha for sha, _ in objects}))
    findings = {}

    def add(rule, path, sha, line=None, match="", detail=None):
        where = "tip" if tip.get(path) == sha else "history"
        fp = fingerprint(rule, path, match)
        findings.setdefault((fp, where), {"rule": rule, "path": path, "where": where, "line": line,
                                          "detail": detail, "fingerprint": fp})

    for sha, path in objects:
        rule = name_rule(path)
        if rule and sha in known:
            add(rule, path, sha)
        content = blobs.get(sha)
        if content is None or b"\0" in content[:8000]:
            continue
        for number, text in enumerate(content.decode("utf-8", "replace").splitlines(), start=1):
            for rule, regex in SECRET_RULES:
                for match in regex.finditer(text):
                    add(rule, path, sha, number, match.group(0))
            for match in PERSONAL_PATH.finditer(text):
                if match.group(1).lower() not in GENERIC_USERS:
                    add("personal-path", path, sha, number, match.group(0), match.group(0))
    return sorted(findings.values(), key=lambda f: (f["path"], f["line"] or 0, f["rule"], f["where"]))


def describe_finding(finding: dict) -> str:
    where = "dernier commit" if finding["where"] == "tip" else "historique publié"
    line = ":%d" % finding["line"] if finding["line"] else ""
    detail = " (%s)" % finding["detail"] if finding["detail"] else ""
    return "  [%s] %s%s — %s%s — empreinte %s" % (finding["rule"], finding["path"], line, where, detail,
                                                   finding["fingerprint"])


def findings_error(pub: dict, pending) -> SyncError:
    lines = ["publication %r bloquée : %d constat(s) de contenu sensible non accepté(s)." % (pub["name"], len(pending))]
    lines += [describe_finding(f) for f in pending]
    lines.append(
        "Correction : retirer le fichier du suivi dans la source (`git rm --cached`, puis .gitignore). "
        "Un constat « historique publié » survit à cette suppression : passer en `strategy=snapshot` "
        "(export sans historique, avec `exclude`), ou accepter le risque en connaissance de cause avec "
        "`accept-findings=true` après avoir révoqué tout secret concerné.")
    return SyncError("\n".join(lines), common.EXIT_FINDINGS, {"findings": pending})


# --------------------------------------------------------------------------- publication

def publish_one(root: str, pub: dict, push: bool, force: bool = False, accept: bool = False) -> dict:
    remote = pub["remote"]
    source_sha = fetch_branch(root, remote, pub["branch"])
    result = {"name": pub["name"], "source": pub["source"], "branch": pub["branch"],
              "source_sha": source_sha, "export": pub["export"] or pub["branch"],
              "mode": "repository" if pub["source"] == "." else "folder", "findings": []}
    if pub["source"] == ".":
        # Dépôt entier : la branche source est déjà ce que les consommateurs référencent.
        result.update(status="tip", export_sha=source_sha, previous_sha=None)
        return result

    result["files"] = check_source_tree(root, source_sha, pub["source"])
    previous = remote_heads(root, remote).get(pub["export"])
    if previous:
        git(["fetch", "--no-tags", remote, "refs/heads/" + pub["export"]], cwd=root)
    if pub["strategy"] == "snapshot":
        new = snapshot_commit(root, source_sha, pub["source"], pub["exclude"], previous)
    else:
        new = subtree_split(root, source_sha, pub["source"])
    result.update(export_sha=new, previous_sha=previous)
    if new == previous:
        result["status"] = "unchanged"
        return result
    if previous is None:
        transition = "created"
    elif common.is_ancestor(root, previous, new):
        transition = "updated"
    else:
        transition = "diverged"

    findings = scan(root, new, previous if transition == "updated" else None)
    result["findings"] = findings
    pending = [f for f in findings if f["fingerprint"] not in pub["accepted_findings"]]
    if pending and accept:
        pub["accepted_findings"] = sorted(set(pub["accepted_findings"]) | {f["fingerprint"] for f in pending})
        pending = []
    if pending:
        raise findings_error(pub, pending)

    forced = transition == "diverged"
    if forced and not (force or pub["allow_force"]):
        raise SyncError(
            "publication %r : la branche d'export %s (%s) n'est pas un ancêtre du nouvel export (%s). "
            "Soit l'historique du dossier source a été réécrit, soit cette branche porte des commits "
            "étrangers à l'export. Rien n'est écrasé par défaut : vérifier, puis relancer avec "
            "`force=true` (ponctuel) ou `allow-force=true` (durable). Les consommateurs devront alors "
            "autoriser eux aussi une mise à jour non fast-forward."
            % (pub["name"], pub["export"], previous[:12], new[:12]), common.EXIT_DIVERGED, result)
    if not push:
        result["status"] = "would-" + transition
        return result
    args = ["push", remote]
    if forced:
        # Jamais de force aveugle : le push échoue si la branche a bougé depuis la lecture.
        args.append("--force-with-lease=refs/heads/%s:%s" % (pub["export"], previous))
    args.append("%s:refs/heads/%s" % (new, pub["export"]))
    proc = git(args, cwd=root, check=False)
    if proc.returncode != 0:
        raise SyncError("push de la branche d'export %s refusé : %s" % (pub["export"], proc.stderr.strip()),
                        common.EXIT_PUSH, result)
    result["status"] = "forced" if forced else transition
    return result


def api_base() -> str:
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not (base.startswith("https://") or re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", base)):
        raise SyncError("GITHUB_API_URL refusée : %r (https attendu)" % base, common.EXIT_USAGE)
    return base


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Une redirection n'est pas suivie : le jeton ne part jamais vers un autre hôte."""

    def redirect_request(self, *args, **kwargs):
        return None


def notify(root: str, pub: dict, result: dict) -> list:
    """Envoie un `repository_dispatch` à chaque consommateur inscrit. Retourne les échecs."""
    if not pub["consumers"]:
        return []
    token = os.environ.get(DISPATCH_TOKEN_ENV, "").strip()
    if not token:
        warn("publication %r : %d consommateur(s) inscrit(s) mais le secret %s est absent. Aucune "
             "notification envoyée ; ils se mettront à jour à leur prochaine exécution planifiée."
             % (pub["name"], len(pub["consumers"]), DISPATCH_TOKEN_ENV))
        return []
    source_repo = os.environ.get("GITHUB_REPOSITORY") or common.url_slug(remote_url(root, pub["remote"]))
    if not source_repo:
        raise SyncError("identité du dépôt source inconnue (GITHUB_REPOSITORY absent, remote non reconnu)")
    body = json.dumps({"event_type": common.EVENT_TYPE, "client_payload": {
        "source_repo": source_repo, "branch": result["export"], "sha": result["export_sha"],
        "source_sha": result["source_sha"], "publication": pub["name"]}}).encode("utf-8")
    failures = []
    for consumer in pub["consumers"]:
        request = urllib.request.Request(
            "%s/repos/%s/dispatches" % (api_base(), consumer), data=body, method="POST",
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                     "User-Agent": "submodule-sync"})
        try:
            with urllib.request.build_opener(_NoRedirect).open(request, timeout=30) as response:
                response.read()
            log("  notifié : %s" % consumer)
        except urllib.error.HTTPError as exc:
            failures.append("%s : HTTP %d (jeton sans accès « Contents: write » à ce dépôt, ou dépôt "
                            "introuvable)" % (consumer, exc.code))
        except (urllib.error.URLError, OSError) as exc:
            failures.append("%s : %s" % (consumer, exc))
    return failures


def describe_result(result: dict) -> str:
    labels = {"tip": "dépôt entier, rien à extraire", "unchanged": "inchangé", "created": "branche créée",
              "updated": "mis à jour", "forced": "réécrit (force avec bail)",
              "would-created": "serait créée", "would-updated": "serait mise à jour",
              "would-diverged": "serait réécrite"}
    return "%s : %s -> %s @ %s [%s] (source %s)" % (
        result["name"], result["source"], result["export"], (result.get("export_sha") or "?")[:12],
        labels.get(result["status"], result["status"]), result["source_sha"][:12])


# --------------------------------------------------------------------------- fichiers gérés

def render_workflow(cfg: dict, script_file: str):
    pubs = [p for p in cfg["publications"] if p["auto"]]
    if not pubs:
        return None
    branches = ", ".join(common.yaml_str(b) for b in sorted({p["branch"] for p in pubs}))
    if any(p["source"] == "." for p in pubs):
        paths_block = "    # Pas de filtre de chemins : une publication porte sur le dépôt entier."
    else:
        paths = sorted({p["source"] + "/**" for p in pubs})
        paths += [CONFIG_PATH, common.SYNC_DIR + "/**", WORKFLOW_PATH]
        paths_block = "    paths:\n" + "\n".join("      - " + common.yaml_str(p) for p in paths)
    return common.render_template(common.read_template(script_file, "submodule-publish.yml.tmpl"), {
        "BRANCHES": branches,
        "PATHS_BLOCK": paths_block,
        "CONTENTS_PERMISSION": "write" if any(p["source"] != "." for p in pubs) else "read",
    })


def install_command(root: str, pub: dict) -> str:
    target = "<chemin-cible>" if pub["source"] == "." else pub["source"]
    quote = '"%s"' if " " in target else "%s"
    return "/install-git-submodule url=%s branch=%s target=%s auto=true" % (
        remote_url(root, pub["remote"]), pub["export"] or pub["branch"], quote % target)


def render_doc(root: str, cfg: dict, script_file: str) -> str:
    rows = []
    for pub in cfg["publications"]:
        rows.append("| `%s` | `%s` | `%s` | `%s` | %s | %s |" % (
            pub["name"], pub["source"], pub["branch"], pub["export"] or pub["branch"],
            "dépôt entier" if pub["source"] == "." else pub["strategy"],
            ", ".join("`%s`" % c for c in pub["consumers"]) or "aucun"))
    commands = "\n".join("- `%s` : `%s`" % (p["name"], install_command(root, p)) for p in cfg["publications"])
    return common.render_template(common.read_template(script_file, "PUBLISH.md.tmpl"),
                                  {"PUBLICATIONS": "\n".join(rows), "INSTALL_COMMANDS": commands})


def write_managed_files(root: str, cfg: dict, script_file: str) -> list:
    """Écrit configuration, scripts, workflow et notice. Retourne les chemins gérés."""
    here = os.path.dirname(os.path.abspath(script_file))
    paths = [CONFIG_PATH, DOC_PATH]
    save_config(root, cfg)
    for name in SCRIPT_FILES:
        rel = "%s/%s" % (common.SYNC_DIR, name)
        if os.path.normcase(os.path.abspath(os.path.join(root, rel))) != os.path.normcase(os.path.join(here, name)):
            common.copy_file(os.path.join(here, name), os.path.join(root, rel))
        paths.append(rel)
    workflow = render_workflow(cfg, script_file)
    if workflow is not None:
        common.write_text(os.path.join(root, WORKFLOW_PATH), workflow)
        paths.append(WORKFLOW_PATH)
    common.write_text(os.path.join(root, DOC_PATH), render_doc(root, cfg, script_file))
    return paths


# --------------------------------------------------------------------------- commandes

def local_warnings(root: str, pub: dict) -> list:
    """Ce qui existe sur le poste mais ne sera pas publié : seul le remote fait foi."""
    notes = []
    scope = [] if pub["source"] == "." else ["--", pub["source"]]
    local = git(["rev-parse", "-q", "--verify", "refs/heads/" + pub["branch"]], cwd=root, check=False)
    if local.returncode == 0:
        ahead = git_out(["rev-list", "--count", "refs/remotes/%s/%s..refs/heads/%s"
                         % (pub["remote"], pub["branch"], pub["branch"])] + scope, cwd=root)
        if ahead != "0":
            notes.append("%s commit(s) local(aux) non poussé(s) sur %s : non publiés" % (ahead, pub["branch"]))
    dirty = [l for l in git(["status", "--porcelain"] + scope, cwd=root).stdout.splitlines() if l.strip()]
    if dirty:
        notes.append("%d fichier(s) modifié(s) ou non suivi(s) sur le poste : non publiés (seuls les "
                     "commits de la branche distante le sont)" % len(dirty))
    return notes


def draft_publication(root: str, cfg: dict, args):
    """Publication demandée, fusionnée avec celle qui existe déjà sous ce nom. Retourne (pub, existante)."""
    source = common.validate_rel_path(args.source, "source", allow_root=True)
    common.ensure_inside(root, source)
    whole = source == "."
    name = args.name or ("repo" if whole else common.slugify(source))
    existing = find_publication(cfg, name)
    if existing and existing["source"] != source:
        raise SyncError("la publication %r existe déjà pour %r : choisir un autre `name`"
                        % (name, existing["source"]), common.EXIT_USAGE)
    known = existing or {}
    remote = common.validate_remote(args.remote or known.get("remote") or "origin")
    remote_url(root, remote)
    branch = args.branch or known.get("branch") or common.default_branch(root, remote)
    if not branch:
        raise SyncError("branche source indéterminée : préciser `branch=`", common.EXIT_USAGE)
    draft = dict(known, name=name, source=source, branch=branch, remote=remote)
    draft["export"] = None if whole else (args.export or known.get("export") or "submodule/" + common.slugify(source))
    for key, value in (("strategy", args.strategy), ("auto", args.auto), ("allow_force", args.allow_force)):
        if value is not None:
            draft[key] = value
    if args.exclude is not None:
        draft["exclude"] = [p for p in args.exclude if p]
    draft["consumers"] = list(known.get("consumers") or []) + list(args.consumer or [])
    return normalize_publication(draft), existing


def check_export_branch(root: str, cfg: dict, pub: dict, is_new: bool, force: bool) -> None:
    """Refuse une branche d'export qui en gênerait une autre ou en écraserait une sans rapport."""
    export, remote = pub["export"], pub["remote"]
    for other in cfg["publications"]:
        if other["name"] != pub["name"] and export in (other["export"], other["branch"]):
            raise SyncError("la branche %s est déjà utilisée par la publication %r" % (export, other["name"]),
                            common.EXIT_USAGE)
    if export == common.default_branch(root, remote):
        raise SyncError("la branche d'export ne peut pas être la branche par défaut (%s)" % export,
                        common.EXIT_USAGE)
    heads = remote_heads(root, remote)
    clash = [h for h in heads if h != export and (h.startswith(export + "/") or export.startswith(h + "/"))]
    if clash:
        raise SyncError("la branche %s ne peut pas coexister avec la branche distante %s (git range "
                        "les branches comme des fichiers)" % (export, clash[0]), common.EXIT_USAGE)
    if export in heads and is_new and pub["strategy"] == "snapshot" and not force:
        # Un instantané se pose en avance rapide sur n'importe quelle branche : sans cette garde,
        # il remplacerait le contenu d'une branche de travail qui porte par hasard ce nom.
        git(["fetch", "--no-tags", remote, "refs/heads/" + export], cwd=root)
        if "Source-Path: " not in git_out(["log", "-1", "--format=%B", heads[export]], cwd=root):
            raise SyncError(
                "la branche %s existe déjà sur %s et n'est pas un export de ce skill : un instantané "
                "y remplacerait tout son contenu. Choisir un autre `export`, ou confirmer avec "
                "force=true." % (export, remote), common.EXIT_DECISION)


def record_publication(root: str, cfg: dict, pub: dict, existing, args, report: dict) -> None:
    """Inscrit la publication, écrit les fichiers gérés, puis commite et pousse si c'est demandé."""
    if existing:
        cfg["publications"][cfg["publications"].index(existing)] = pub
    else:
        cfg["publications"].append(pub)
    report["files"] = write_managed_files(root, cfg, __file__)
    if not args.commit:
        return
    subject = "le dépôt" if pub["source"] == "." else pub["source"]
    report["commit"] = common.commit_paths(root, report["files"],
                                           "ci(submodule): publier %s comme source de sous-module" % subject)
    if args.push and report["commit"]:
        refusal = common.push_current_branch(root, pub["remote"])
        report["pushed"] = refusal is None
        if refusal:
            report["warnings"].append("push de la configuration refusé ou impossible : %s" % refusal)


def print_setup_report(root: str, pub: dict, report: dict, as_json: bool) -> None:
    log(describe_result(report["result"]))
    for finding in report["result"]["findings"]:
        log(describe_finding(finding) + " (accepté)")
    for note in report["warnings"]:
        warn(note)
    if not report["dry_run"]:
        log("Fichiers gérés : " + ", ".join(report["files"]))
        if pub["auto"] and common.current_branch(root) != pub["branch"]:
            warn("le workflow n'agira qu'une fois présent sur la branche source %s (et sur la branche "
                 "par défaut pour le déclenchement manuel)" % pub["branch"])
    log("Installation chez un consommateur : " + report["install_command"])
    if as_json:
        log(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_setup(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    pub, existing = draft_publication(root, cfg, args)
    if pub["export"]:
        check_export_branch(root, cfg, pub, existing is None, args.force)
    publish = not (args.dry_run or args.no_publish)
    result = publish_one(root, pub, push=publish, force=args.force, accept=args.accept_findings)
    report = {"root": root, "remote_url": remote_url(root, pub["remote"]), "publication": pub,
              "result": result, "warnings": local_warnings(root, pub),
              "install_command": install_command(root, pub), "dry_run": args.dry_run}
    if not args.dry_run:
        record_publication(root, cfg, pub, existing, args, report)
    print_setup_report(root, pub, report, args.json)
    return common.EXIT_OK


def cmd_run(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    if args.name:
        pubs = [require_publication(cfg, args.name)]
    else:
        pubs = list(cfg["publications"])
        if os.environ.get("GITHUB_EVENT_NAME") == "push" and os.environ.get("GITHUB_REF_NAME"):
            # Un push ne concerne que les publications de sa branche.
            pubs = [p for p in pubs if p["branch"] == os.environ["GITHUB_REF_NAME"]]
    if not pubs:
        log("Aucune publication à traiter.")
        return common.EXIT_OK
    always = args.notify_always or os.environ.get("SUBMODULE_NOTIFY_ALWAYS", "").lower() == "true"
    code, rows = common.EXIT_OK, []
    for pub in pubs:
        try:
            result = publish_one(root, pub, push=args.push, force=args.force)
            log(describe_result(result))
            changed = result["status"] in ("created", "updated", "forced")
            # Un dépôt entier n'a pas d'état d'export : chaque push de sa branche est une nouvelle version.
            if args.notify and args.push and (changed or always or result["status"] == "tip"):
                failures = notify(root, pub, result)
                for failure in failures:
                    common.error("notification échouée — " + failure)
                if failures:
                    code = code or common.EXIT_ERROR
            rows.append("| `%s` | `%s` | `%s` | `%s` | %s |" % (
                pub["name"], result["export"], result["source_sha"][:12],
                (result.get("export_sha") or "")[:12], result["status"]))
        except SyncError as exc:
            common.error(str(exc))
            code = code or exc.code
            rows.append("| `%s` | `%s` | | | échec (code %d) |" % (pub["name"], pub["export"] or pub["branch"], exc.code))
    common.step_summary("### Publication des sous-modules\n\n| Publication | Branche | Source | Export | État |\n"
                        "|---|---|---|---|---|\n" + "\n".join(rows))
    return code


def cmd_register(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    pub = require_publication(cfg, args.name)
    consumer = common.validate_slug(args.consumer, "consommateur")
    present = [c for c in pub["consumers"] if c.lower() == consumer.lower()]
    if args.remove:
        pub["consumers"] = [c for c in pub["consumers"] if c.lower() != consumer.lower()]
    elif not present:
        pub["consumers"].append(consumer)
    paths = write_managed_files(root, cfg, __file__) if os.path.isdir(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")) else [CONFIG_PATH]
    if paths == [CONFIG_PATH]:
        save_config(root, cfg)
    log("Publication %r — consommateurs notifiés : %s" % (pub["name"], ", ".join(pub["consumers"]) or "aucun"))
    if args.commit:
        sha = common.commit_paths(root, paths, "ci(submodule): %s le consommateur %s de %s"
                                  % ("retirer" if args.remove else "inscrire", consumer, pub["name"]))
        log("Commit : %s" % (sha or "aucun changement"))
    if pub["consumers"]:
        log("Rappel : le secret %s doit exister dans ce dépôt, avec « Contents: write » sur chaque "
            "consommateur. Sans lui, seule la planification des consommateurs les met à jour." % DISPATCH_TOKEN_ENV)
    return common.EXIT_OK


def cmd_status(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    code = common.EXIT_OK
    for pub in cfg["publications"]:
        try:
            result = publish_one(root, pub, push=False)
            log(describe_result(result))
        except SyncError as exc:
            common.error(str(exc))
            code = code or exc.code
    if not cfg["publications"]:
        log("Aucune publication configurée dans %s." % CONFIG_PATH)
    return code


def cmd_render(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = load_config(root)
    log("Fichiers régénérés : " + ", ".join(write_managed_files(root, cfg, __file__)))
    return common.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    flag = dict(nargs="?", const=True, default=False, type=common.parse_bool)
    parser = argparse.ArgumentParser(description="Publication d'une source de sous-module.")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="préparer et publier")
    setup.add_argument("--source", default=".", help="`.` pour le dépôt entier, sinon un dossier")
    setup.add_argument("--branch", help="branche source (défaut : branche par défaut du remote)")
    setup.add_argument("--export", help="branche d'export (défaut : submodule/<dossier>)")
    setup.add_argument("--name", help="identifiant de la publication")
    setup.add_argument("--remote", help="remote (défaut : origin)")
    setup.add_argument("--strategy", choices=["subtree", "snapshot"])
    setup.add_argument("--exclude", action="append", help="motif exclu de l'export (snapshot seulement)")
    setup.add_argument("--auto", nargs="?", const=True, default=None, type=common.parse_bool,
                       help="installer le workflow de publication automatique (défaut : true)")
    setup.add_argument("--allow-force", dest="allow_force", nargs="?", const=True, default=None,
                       type=common.parse_bool)
    setup.add_argument("--consumer", action="append", help="dépôt consommateur à notifier")
    setup.add_argument("--accept-findings", dest="accept_findings", **flag)
    setup.add_argument("--dry-run", dest="dry_run", **flag)
    setup.add_argument("--no-publish", dest="no_publish", **flag)
    setup.add_argument("--commit", **flag)
    setup.add_argument("--push", **flag)
    setup.add_argument("--force", **flag)
    setup.add_argument("--json", action="store_true")
    setup.set_defaults(func=cmd_setup)

    run = sub.add_parser("run", help="publier les exports configurés")
    run.add_argument("--name")
    run.add_argument("--all", action="store_true", help="toutes les publications (défaut)")
    run.add_argument("--push", **flag)
    run.add_argument("--notify", **flag)
    run.add_argument("--notify-always", dest="notify_always", **flag)
    run.add_argument("--force", **flag)
    run.set_defaults(func=cmd_run)

    for command, remove in (("register", False), ("unregister", True)):
        reg = sub.add_parser(command)
        reg.add_argument("--name", required=True)
        reg.add_argument("--consumer", required=True)
        reg.add_argument("--commit", **flag)
        reg.set_defaults(func=cmd_register, remove=remove)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("render").set_defaults(func=cmd_render)
    return parser


def main(argv) -> int:
    args = build_parser().parse_args(common.kv_to_argv(argv, KV_KEYS))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(common.run_main(main))
