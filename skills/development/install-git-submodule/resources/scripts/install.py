#!/usr/bin/env python3
"""Installe un sous-module dans le dépôt courant et sa mise à jour automatique.

Commandes :
  apply    installe ou vérifie le sous-module, puis écrit configuration, script et workflow
  render   régénère workflow et notice à partir de la configuration

`apply dry-run=true` n'écrit rien et décrit ce qui serait fait. Un dossier cible déjà présent
n'est jamais supprimé ni écrasé directement : il est comparé au contenu à installer, sauvegardé en
entier, et toute divergence demande un choix explicite (`migrate=preserve`).

Les paramètres s'écrivent `--clé valeur` ou `clé=valeur`. Bibliothèque standard, Python 3.8+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update as engine
common = engine.common
SyncError, git, git_out, log, warn = common.SyncError, common.git, common.git_out, common.log, common.warn

KV_KEYS = {"url", "branch", "target", "name", "auto", "schedule", "target-branch", "mode", "check",
           "migrate", "set-url", "set-branch", "allow-nested", "force-ignored", "commit", "push",
           "dry-run", "remote"}
LIST_LIMIT = 40
GITMODULES = ".gitmodules"


# --------------------------------------------------------------------------- inspection

def file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(base: str) -> dict:
    """{chemin relatif: empreinte} de tous les fichiers d'un dossier, hors métadonnées git."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if name == ".git":
                continue
            full = os.path.join(dirpath, name)
            found[os.path.relpath(full, base).replace(os.sep, "/")] = file_hash(full)
    return found


def probe_remote(root: str, url: str, branch: str) -> str:
    """Vérifie l'accès en lecture et l'existence de la branche. Retourne sa tête."""
    proc = git(["ls-remote", "--heads", "--", url], cwd=root, check=False)
    if proc.returncode != 0:
        raise SyncError("dépôt source inaccessible en lecture : %s\n%s" % (url, proc.stderr.strip()),
                        common.EXIT_ACCESS)
    heads = {}
    for line in proc.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            heads[ref[len("refs/heads/"):]] = sha
    if branch not in heads:
        raise SyncError("la branche %r n'existe pas dans %s (branches : %s). Pour un dossier, lancer "
                        "d'abord /publish-git-submodule dans le dépôt source."
                        % (branch, url, ", ".join(sorted(heads)) or "aucune"), common.EXIT_ACCESS)
    return heads[branch]


def snapshot_remote(root: str, url: str, branch: str) -> dict:
    """Empreintes du contenu de la branche à installer, lues dans un clone temporaire."""
    tmp = tempfile.mkdtemp(prefix="submodule-install-")
    try:
        git(["clone", "-q", "--depth", "1", "--single-branch", "--branch", branch, "--", url, tmp], cwd=root)
        return tree_hashes(tmp)
    finally:
        common.force_rmtree(tmp)


def target_state(root: str, target: str, modules: dict) -> str:
    staged = git(["ls-files", "-s", "--", target], cwd=root).stdout.splitlines()
    if any(line.startswith("160000 ") and line.split("\t", 1)[-1] == target for line in staged):
        return "submodule"
    if target in modules:
        raise SyncError("%s est déclaré dans .gitmodules mais n'est pas enregistré comme sous-module : "
                        "état incohérent à corriger à la main (`git submodule status`)" % target,
                        common.EXIT_DECISION)
    full = os.path.join(root, target)
    if os.path.isfile(full):
        raise SyncError("%s est un fichier : un sous-module s'installe dans un dossier" % target,
                        common.EXIT_USAGE)
    if staged or (os.path.isdir(full) and any(files for _, _, files in os.walk(full))):
        return "directory"
    return "absent"


def compare_directory(root: str, target: str, remote_files: dict) -> dict:
    full = os.path.join(root, target)
    for dirpath, dirnames, filenames in os.walk(full):
        if ".git" in dirnames or ".git" in filenames:
            raise SyncError("%s contient un dépôt git imbriqué (%s) : le traiter à la main avant "
                            "l'installation" % (target, os.path.relpath(dirpath, root)), common.EXIT_DECISION)
    local = tree_hashes(full) if os.path.isdir(full) else {}
    prefix = target + "/"
    tracked = {p[len(prefix):] for p in git(["ls-files", "-z", "--", prefix], cwd=root).stdout.split("\0")
               if p.startswith(prefix)}
    modified = {l[3:].strip('"')[len(prefix):] for l in
                git(["status", "--porcelain", "--", prefix], cwd=root).stdout.splitlines()
                if l[:2].strip() and not l.startswith("??")}
    only_local = sorted(set(local) - set(remote_files))
    return {
        "identical": sorted(p for p in local if remote_files.get(p) == local[p]),
        "differing": sorted(p for p in local if p in remote_files and remote_files[p] != local[p]),
        "local_only_tracked": [p for p in only_local if p in tracked],
        "local_only_untracked": [p for p in only_local if p not in tracked],
        "remote_only": sorted(set(remote_files) - set(local)),
        "modified_tracked": sorted(modified),
    }


def needs_decision(comparison: dict) -> bool:
    return bool(comparison["differing"] or comparison["local_only_tracked"] or comparison["local_only_untracked"])


def describe_comparison(target: str, comparison: dict) -> str:
    labels = [
        ("identical", "identiques à la source (aucune perte)"),
        ("differing", "présents des deux côtés avec un contenu DIFFÉRENT — la version de la source "
                      "s'installera, la vôtre ira dans la sauvegarde"),
        ("local_only_tracked", "suivis ici et ABSENTS de la source — ils cesseront d'être versionnés "
                               "dans ce dépôt (replacés non suivis dans le sous-module, et sauvegardés) ; "
                               "ils ne sont pas envoyés à la source"),
        ("local_only_untracked", "non suivis ici et absents de la source — replacés tels quels, non suivis"),
        ("remote_only", "apportés par la source"),
        ("modified_tracked", "modifiés par rapport au dernier commit (la version du disque est sauvegardée)"),
    ]
    lines = ["Contenu actuel de %s comparé à la source :" % target]
    for key, label in labels:
        items = comparison[key]
        if not items:
            continue
        lines.append("  %d fichier(s) %s" % (len(items), label))
        lines += ["    - %s" % p for p in items[:LIST_LIMIT]]
        if len(items) > LIST_LIMIT:
            lines.append("    … et %d autre(s)" % (len(items) - LIST_LIMIT))
    return "\n".join(lines)


# --------------------------------------------------------------------------- migration

def backup_directory(root: str, target: str, comparison: dict) -> str:
    """Copie intégrale du dossier dans le répertoire git (jamais commité, jamais supprimé ici)."""
    common_dir = git_out(["rev-parse", "--git-common-dir"], cwd=root)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = os.path.join(os.path.abspath(os.path.join(root, common_dir)), "submodule-sync-backups",
                          "%s-%s" % (common.slugify(target), stamp))
    source = os.path.join(root, target)
    shutil.copytree(source, os.path.join(backup, "files"), symlinks=True)
    if tree_hashes(source) != tree_hashes(os.path.join(backup, "files")):
        raise SyncError("la sauvegarde de %s ne correspond pas à l'original : rien n'a été modifié" % target)
    patch = git(["diff", "--binary", "HEAD", "--", target], cwd=root, check=False).stdout
    if patch.strip():
        common.write_text(os.path.join(backup, "tracked-changes.patch"), patch)
    common.dump_json(os.path.join(backup, "MANIFEST.json"), {"target": target, "comparison": comparison})
    return backup


def restore_from_backup(root: str, target: str, backup: str) -> None:
    """Annule une migration qui a échoué en route : le dossier et l'index retrouvent leur état."""
    full = os.path.join(root, target)
    common.force_rmtree(full)
    shutil.copytree(os.path.join(backup, "files"), full, symlinks=True)
    git(["reset", "-q", "HEAD", "--", target], cwd=root, check=False)


def add_submodule(root: str, args, url: str, branch: str, target: str) -> None:
    """`git submodule add`, annulé entièrement s'il échoue en route."""
    gitmodules = os.path.join(root, GITMODULES)
    before = None
    if os.path.isfile(gitmodules):
        with open(gitmodules, "rb") as fh:
            before = fh.read()
    common_dir = os.path.abspath(os.path.join(root, git_out(["rev-parse", "--git-common-dir"], cwd=root)))
    module_dir = os.path.join(common_dir, "modules", *(args.name or target).split("/"))
    had_module_dir = os.path.isdir(module_dir)
    command = ["submodule", "add", "-q"] + (["-f"] if args.force_ignored else []) + ["-b", branch]
    if args.name:
        command += ["--name", args.name]
    try:
        proc = git(command + ["--", url, target], cwd=root, check=False)
        if proc.returncode != 0:
            raise SyncError("`git submodule add` a échoué : %s" % proc.stderr.strip(), common.EXIT_ERROR)
        if engine.read_gitmodules(root).get(target, {}).get("branch") != branch:
            git(["submodule", "set-branch", "--branch", branch, "--", target], cwd=root)
    except SyncError:
        git(["rm", "-q", "--cached", "--ignore-unmatch", "--", target], cwd=root, check=False)
        common.force_rmtree(os.path.join(root, target))
        if not had_module_dir:
            common.force_rmtree(module_dir)
        git(["reset", "-q", "HEAD", "--", GITMODULES], cwd=root, check=False)
        if before is None:
            if os.path.isfile(gitmodules):
                os.remove(gitmodules)
        else:
            with open(gitmodules, "wb") as fh:
                fh.write(before)
        raise


def install_fresh(root: str, args, url: str, branch: str, target: str, report: dict) -> None:
    remote_files = snapshot_remote(root, url, branch)
    base = target.rsplit("/", 1)[-1]
    if any(p.startswith(base + "/") for p in remote_files) and not args.allow_nested:
        raise SyncError(
            "la branche %s contient elle-même un dossier %s/ : l'installer dans %s produirait %s/%s. "
            "C'est probablement la branche du dépôt entier et non la branche d'export du dossier "
            "(submodule/…). Si c'est voulu : allow-nested=true." % (branch, base, target, target, base),
            common.EXIT_DECISION)
    if git(["check-ignore", "-q", "--", target], cwd=root, check=False).returncode == 0 and not args.force_ignored:
        raise SyncError("%s est ignoré par un .gitignore de ce dépôt : corriger la règle, ou relancer "
                        "avec force-ignored=true" % target, common.EXIT_DECISION)
    state = report["state"]
    comparison = backup = None
    if state == "directory":
        comparison = compare_directory(root, target, remote_files)
        report["comparison"] = comparison
        log(describe_comparison(target, comparison))
        if needs_decision(comparison) and args.migrate != "preserve":
            raise SyncError(
                "%s existe déjà et diffère de la source : rien n'a été modifié. Décision requise — "
                "relancer avec migrate=preserve pour appliquer exactement ce qui est décrit ci-dessus "
                "(sauvegarde intégrale, aucun fichier supprimé définitivement), ou déplacer d'abord "
                "ces fichiers." % target, common.EXIT_DECISION, report)
    if args.dry_run:
        report["action"] = "would-migrate" if state == "directory" else "would-add"
        return
    if state == "directory":
        backup = backup_directory(root, target, comparison)
        report["backup"] = backup
        git(["rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", target], cwd=root)
        common.force_rmtree(os.path.join(root, target))
    try:
        add_submodule(root, args, url, branch, target)
    except SyncError:
        if backup:
            restore_from_backup(root, target, backup)
            warn("installation interrompue : %s a été remis dans son état d'origine" % target)
        raise
    if comparison:
        restored = []
        for rel in comparison["local_only_tracked"] + comparison["local_only_untracked"]:
            destination = os.path.join(root, target, rel)
            if not os.path.lexists(destination):
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copy2(os.path.join(backup, "files", rel), destination)
                restored.append(rel)
        report["restored_untracked"] = restored
    report["action"] = "migrated" if state == "directory" else "added"


def same_url(left: str, right: str) -> bool:
    def norm(url):
        slug = common.url_slug(url)
        return slug.lower() if slug else url.rstrip("/")[:-4] if url.rstrip("/").endswith(".git") else url.rstrip("/")
    return norm(left) == norm(right)


def reconcile_submodule(root: str, args, url: str, branch: str, target: str, modules: dict, report: dict) -> None:
    """Le chemin est déjà un sous-module : vérifier, ou reconfigurer sur demande explicite."""
    module = modules.get(target)
    if not module:
        raise SyncError("%s est un sous-module sans entrée dans .gitmodules : état à corriger à la main" % target,
                        common.EXIT_DECISION)
    changes = []
    if not same_url(module["url"], url):
        if not args.set_url:
            raise SyncError("%s est déjà un sous-module de %s, pas de %s : rien n'a été modifié. Pour "
                            "changer de source : set-url=true." % (target, module["url"], url),
                            common.EXIT_DECISION, report)
        changes.append("url")
    current = module.get("branch")
    if current != branch:
        if current and not args.set_branch:
            raise SyncError("%s suit déjà la branche %s, pas %s : rien n'a été modifié. Pour changer de "
                            "branche : set-branch=true." % (target, current, branch), common.EXIT_DECISION, report)
        changes.append("branch")
    report["action"] = ("would-reconfigure" if changes else "would-verify") if args.dry_run else \
        ("reconfigured" if changes else "verified")
    report["changes"] = changes
    if args.dry_run:
        return
    if "url" in changes:
        git(["submodule", "set-url", "--", target, url], cwd=root)
        git(["submodule", "sync", "-q", "--", target], cwd=root)
    if "branch" in changes:
        git(["submodule", "set-branch", "--branch", branch, "--", target], cwd=root)
    if not os.path.exists(os.path.join(root, target, ".git")):
        git(["submodule", "update", "--init", "--", target], cwd=root)


# --------------------------------------------------------------------------- automatisation

def render_workflow(cfg: dict, script_file: str) -> str:
    if cfg["schedule"]:
        schedule = "  schedule:\n    - cron: %s" % common.yaml_str(cfg["schedule"])
    else:
        schedule = "  # Pas de planification : seuls l'événement du producteur et le lancement manuel agissent."
    permissions = "  contents: write" + ("\n  pull-requests: write" if cfg["mode"] == "pr" else "")
    return common.render_template(common.read_template(script_file, "submodule-update.yml.tmpl"), {
        "SCHEDULE_BLOCK": schedule,
        "PERMISSIONS": permissions,
        "TARGET_BRANCH": common.yaml_str(cfg["target_branch"]),
        "CONCURRENCY_GROUP": "submodule-update-" + common.slugify(cfg["target_branch"]),
    })


def render_doc(root: str, cfg: dict, script_file: str) -> str:
    modules = engine.read_gitmodules(root)
    rows = []
    for entry in cfg["submodules"]:
        module = modules.get(entry["path"], {})
        rows.append("| `%s` | `%s` | `%s` | %s | %s |" % (
            entry["path"], module.get("url", "?"), module.get("branch", "?"),
            "<br>".join("`%s`" % c for c in cfg["checks"] + entry["checks"]) or "aucun",
            "suspendu" if entry["hold"] else "automatique"))
    return common.render_template(common.read_template(script_file, "UPDATE.md.tmpl"), {
        "SUBMODULES": "\n".join(rows),
        "TARGET_BRANCH": cfg["target_branch"],
        "MODE": "pull request avec fusion automatique" if cfg["mode"] == "pr" else "push direct",
        "SCHEDULE": "`%s` (UTC)" % cfg["schedule"] if cfg["schedule"] else "aucune",
    })


def write_managed_files(root: str, cfg: dict, script_file: str) -> list:
    here = os.path.dirname(os.path.abspath(script_file))
    common.dump_json(os.path.join(root, engine.CONFIG_PATH), cfg)
    paths = [engine.CONFIG_PATH, engine.WORKFLOW_PATH, engine.DOC_PATH]
    paths += common.copy_scripts(root, here, engine.SCRIPT_FILES)
    common.write_text(os.path.join(root, engine.WORKFLOW_PATH), render_workflow(cfg, script_file))
    common.write_text(os.path.join(root, engine.DOC_PATH), render_doc(root, cfg, script_file))
    return paths


def configure_automation(root: str, args, target: str) -> list:
    cfg = engine.load_config(root)
    if args.remote:
        cfg["remote"] = common.validate_remote(args.remote)
    cfg["target_branch"] = (args.target_branch or cfg["target_branch"]
                            or common.default_branch(root, cfg["remote"]) or common.current_branch(root))
    if not cfg["target_branch"]:
        raise SyncError("branche destinataire indéterminée : préciser target-branch=", common.EXIT_USAGE)
    if args.mode:
        cfg["mode"] = args.mode
    if args.schedule is not None:
        cfg["schedule"] = None if args.schedule.strip().lower() in ("none", "off", "false", "") else args.schedule
    entry = next((e for e in cfg["submodules"] if e["path"] == target), None)
    if entry is None:
        entry = {"path": target, "checks": [], "hold": False, "allow_non_fast_forward": False}
        cfg["submodules"].append(entry)
    for check in args.check or []:
        if check not in entry["checks"]:
            entry["checks"].append(check)
    return write_managed_files(root, engine.normalize_config(cfg), __file__)


# --------------------------------------------------------------------------- commandes

def cmd_apply(args) -> int:
    root = common.repo_root(os.getcwd())
    url, branch = args.url, common.validate_branch(args.branch, "branche source")
    kind = common.validate_url(url)
    target = common.validate_rel_path(args.target, "chemin cible")
    common.ensure_inside(root, target)
    if args.migrate not in (None, "preserve"):
        raise SyncError("migrate ne connaît que `preserve`", common.EXIT_USAGE)
    tip = probe_remote(root, url, branch)
    modules = engine.read_gitmodules(root)
    state = target_state(root, target, modules)
    report = {"root": root, "url": url, "branch": branch, "target": target, "state": state,
              "source_tip": tip, "dry_run": args.dry_run}

    if state == "submodule":
        reconcile_submodule(root, args, url, branch, target, modules, report)
    else:
        install_fresh(root, args, url, branch, target, report)

    notes = []
    if kind == "local":
        notes.append("URL locale : utilisable sur ce poste, pas par GitHub Actions")
    if kind == "ssh":
        notes.append("URL SSH : le workflow la réécrit en HTTPS pour s'authentifier par jeton ; préférer "
                     "une URL https:// dans .gitmodules")
    if not args.dry_run:
        paths = [GITMODULES, target]
        if args.auto:
            paths += configure_automation(root, args, target)
        report["files"] = paths
        report["recorded"] = git(["rev-parse", "HEAD"], cwd=os.path.join(root, target), check=False).stdout.strip()
        if args.commit:
            report["commit"] = common.commit_paths(
                root, paths, "chore(submodule): installer %s (%s@%s)" % (target, url, branch))
            if args.push and report["commit"]:
                refusal = common.push_current_branch(root, engine.load_config(root)["remote"])
                report["pushed"] = refusal is None
                if refusal:
                    notes.append("push refusé ou impossible : %s" % refusal)

    log("%s : %s (%s@%s, tête %s)" % (target, report["action"], url, branch, tip[:12]))
    if report.get("backup"):
        log("Sauvegarde intégrale de l'ancien dossier : %s" % report["backup"])
    if report.get("restored_untracked"):
        log("Fichiers locaux replacés non suivis : %d" % len(report["restored_untracked"]))
    for note in notes:
        warn(note)
    if not args.dry_run:
        log("Fichiers gérés : " + ", ".join(report["files"]))
        slug = common.url_slug(git(["remote", "get-url", "origin"], cwd=root, check=False).stdout.strip())
        log("Clonage : git clone --recurse-submodules <url>   (clone existant : git submodule update --init)")
        if args.auto:
            log("Mise à jour sur événement : dans le dépôt source, inscrire ce dépôt — "
                "/publish-git-submodule register name=<publication> consumer=%s" % (slug or "<propriétaire>/<dépôt>"))
    if args.json:
        log(json.dumps(report, ensure_ascii=False, indent=2))
    return common.EXIT_OK


def cmd_render(args) -> int:
    root = common.repo_root(os.getcwd())
    cfg = engine.load_config(root)
    if not cfg["submodules"] or not cfg["target_branch"]:
        raise SyncError("rien à régénérer : %s est absent ou vide" % engine.CONFIG_PATH, common.EXIT_USAGE)
    log("Fichiers régénérés : " + ", ".join(write_managed_files(root, cfg, __file__)))
    return common.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    flag = dict(nargs="?", const=True, default=False, type=common.parse_bool)
    parser = argparse.ArgumentParser(description="Installation d'un sous-module et de sa mise à jour.")
    sub = parser.add_subparsers(dest="command", required=True)
    apply = sub.add_parser("apply", help="installer ou vérifier un sous-module")
    apply.add_argument("--url", required=True)
    apply.add_argument("--branch", required=True, help="branche à suivre dans le dépôt source")
    apply.add_argument("--target", required=True, help="dossier d'installation, relatif à la racine")
    apply.add_argument("--name", help="nom du sous-module (défaut : son chemin)")
    apply.add_argument("--auto", nargs="?", const=True, default=True, type=common.parse_bool)
    apply.add_argument("--schedule", help="cron UTC de la mise à jour planifiée, ou none")
    apply.add_argument("--target-branch", dest="target_branch", help="branche qui reçoit les mises à jour")
    apply.add_argument("--remote", help="remote du dépôt destinataire (défaut : origin)")
    apply.add_argument("--mode", choices=["push", "pr"])
    apply.add_argument("--check", action="append", help="commande de contrôle avant tout commit")
    apply.add_argument("--migrate", help="`preserve` : migrer un dossier existant qui diffère")
    apply.add_argument("--set-url", dest="set_url", **flag)
    apply.add_argument("--set-branch", dest="set_branch", **flag)
    apply.add_argument("--allow-nested", dest="allow_nested", **flag)
    apply.add_argument("--force-ignored", dest="force_ignored", **flag)
    apply.add_argument("--commit", **flag)
    apply.add_argument("--push", **flag)
    apply.add_argument("--dry-run", dest="dry_run", **flag)
    apply.add_argument("--json", action="store_true")
    apply.set_defaults(func=cmd_apply)
    sub.add_parser("render").set_defaults(func=cmd_render)
    return parser


def main(argv) -> int:
    args = build_parser().parse_args(common.kv_to_argv(argv, KV_KEYS))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(common.run_main(main))
