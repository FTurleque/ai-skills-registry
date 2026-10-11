#!/usr/bin/env python3
"""Socle commun des scripts de synchronisation de sous-modules.

Ce fichier est livré à l'identique par les skills `publish-git-submodule` et
`install-git-submodule`, puis copié dans `.github/submodule-sync/` des dépôts qui les utilisent.
Il ne porte que ce que les deux côtés partagent : exécution de git, validation des paramètres,
authentification sans secret persistant, lecture et écriture des fichiers gérés.

Bibliothèque standard seulement, Python 3.8+.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import stat
import subprocess
import sys

COMMON_VERSION = "1.0.0"
SYNC_DIR = ".github/submodule-sync"
EVENT_TYPE = "submodule-updated"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2       # paramètre ou configuration invalide
EXIT_ACCESS = 3      # dépôt, branche ou remote inaccessible
EXIT_DIVERGED = 4    # historique non fast-forward : aucune écriture forcée par défaut
EXIT_FINDINGS = 5    # contenu sensible non accepté
EXIT_PUSH = 6        # push refusé par le remote
EXIT_DECISION = 7    # divergence qui demande un choix de l'utilisateur

SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REMOTE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CRON_RE = re.compile(r"^(?:[0-9A-Za-z*/,-]+ ){4}[0-9A-Za-z*/,-]+$")
_FORBIDDEN = set("*?[]{}\"'`$\\<>|;&")
_BOT_NAME = "github-actions[bot]"
_BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


class SyncError(Exception):
    """Erreur attendue : message lisible, code de sortie, détails pour le rapport JSON."""

    def __init__(self, message: str, code: int = EXIT_ERROR, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


# --------------------------------------------------------------------------- sortie

def setup_output() -> None:
    """La console Windows n'est pas en UTF-8 par défaut : ne jamais planter sur un accent."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "ATTENTION : "
    print(prefix + message.replace("\n", " "), flush=True)


def error(message: str) -> None:
    prefix = "::error::" if os.environ.get("GITHUB_ACTIONS") == "true" else "ERREUR : "
    print(prefix + message.replace("\n", " "), file=sys.stderr, flush=True)


def step_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(markdown.rstrip("\n") + "\n")


# --------------------------------------------------------------------------- git

def git(args, cwd=None, env=None, check=True, input_text=None):
    """Lance git sans shell : chaque argument est transmis tel quel, espaces compris."""
    proc = subprocess.run(["git"] + list(args), cwd=cwd, env=env, input=input_text,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise SyncError("git %s a échoué (code %d) : %s"
                        % (" ".join(list(args)[:2]), proc.returncode, detail))
    return proc


def git_out(args, cwd=None, env=None) -> str:
    return git(args, cwd=cwd, env=env).stdout.strip()


def repo_root(cwd: str) -> str:
    proc = git(["rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if proc.returncode != 0:
        raise SyncError("le répertoire courant n'est pas dans un dépôt Git", EXIT_USAGE)
    return os.path.normpath(proc.stdout.strip())


def current_branch(root: str):
    proc = git(["symbolic-ref", "-q", "--short", "HEAD"], cwd=root, check=False)
    return proc.stdout.strip() or None


def default_branch(root: str, remote: str):
    """Branche par défaut du remote : référence locale, puis interrogation, puis branche courante."""
    proc = git(["symbolic-ref", "-q", "--short", "refs/remotes/%s/HEAD" % remote], cwd=root, check=False)
    name = proc.stdout.strip()
    if proc.returncode == 0 and name.startswith(remote + "/"):
        return name[len(remote) + 1:]
    proc = git(["ls-remote", "--symref", remote, "HEAD"], cwd=root, check=False)
    for line in proc.stdout.splitlines():
        match = re.match(r"^ref: refs/heads/(\S+)\s+HEAD$", line)
        if match:
            return match.group(1)
    return current_branch(root)


def is_ancestor(root: str, old: str, new: str) -> bool:
    return git(["merge-base", "--is-ancestor", old, new], cwd=root, check=False).returncode == 0


def with_git_config(env: dict, pairs) -> dict:
    """Ajoute des réglages git par l'environnement, sans rien écrire dans .git/config."""
    env = dict(env)
    count = int(env.get("GIT_CONFIG_COUNT", "0") or "0")
    for key, value in pairs:
        env["GIT_CONFIG_KEY_%d" % count] = key
        env["GIT_CONFIG_VALUE_%d" % count] = value
        count += 1
    env["GIT_CONFIG_COUNT"] = str(count)
    return env


def auth_env(token, env=None) -> dict:
    """Environnement d'un seul appel git authentifié par jeton.

    Le jeton ne passe ni par une URL, ni par la ligne de commande, ni par .git/config : il n'existe
    que dans l'environnement du processus lancé. Les URL SSH de GitHub sont réécrites en HTTPS,
    seule forme qu'un jeton sait authentifier.
    """
    env = dict(os.environ if env is None else env)
    if not token:
        return env
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    host = server.split("://", 1)[-1]
    basic = base64.b64encode(("x-access-token:" + token).encode("utf-8")).decode("ascii")
    return with_git_config(env, [
        ("http.%s/.extraheader" % server, "AUTHORIZATION: basic " + basic),
        ("url.%s/.insteadOf" % server, "git@%s:" % host),
        ("url.%s/.insteadOf" % server, "ssh://git@%s/" % host),
    ])


def clean_env(env=None) -> dict:
    """Environnement des contrôles : aucun jeton, aucun réglage git injecté."""
    env = dict(os.environ if env is None else env)
    for key in list(env):
        upper = key.upper()
        if "TOKEN" in upper or "SECRET" in upper or "PASSWORD" in upper or upper.startswith("GIT_CONFIG_"):
            del env[key]
    return env


def identity_env(root: str, env=None) -> dict:
    """Identité de commit du robot quand le dépôt n'en a pas (cas d'un runner)."""
    env = dict(os.environ if env is None else env)
    configured = git(["config", "user.name"], cwd=root, env=env, check=False).stdout.strip()
    if not configured and not env.get("GIT_AUTHOR_NAME"):
        env.update(GIT_AUTHOR_NAME=_BOT_NAME, GIT_AUTHOR_EMAIL=_BOT_EMAIL,
                   GIT_COMMITTER_NAME=_BOT_NAME, GIT_COMMITTER_EMAIL=_BOT_EMAIL)
    return env


# --------------------------------------------------------------------------- validation

def validate_rel_path(value, what: str = "chemin", allow_root: bool = False) -> str:
    """Normalise un chemin relatif au dépôt et refuse tout ce qui en sort ou se prête à l'injection."""
    if not isinstance(value, str) or not value.strip():
        raise SyncError("%s vide" % what, EXIT_USAGE)
    raw = value.replace("\\", "/")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise SyncError("%s absolu refusé : %r (attendu : relatif à la racine du dépôt)" % (what, value),
                        EXIT_USAGE)
    while raw.startswith("./"):
        raw = raw[2:]
    raw = raw.rstrip("/")
    if raw in ("", "."):
        if allow_root:
            return "."
        raise SyncError("%s : la racine du dépôt n'est pas acceptée ici" % what, EXIT_USAGE)
    for segment in raw.split("/"):
        if segment in ("", ".", ".."):
            raise SyncError("%s refusé : %r sort du dépôt ou contient un segment vide" % (what, value),
                            EXIT_USAGE)
        if segment.lower() == ".git":
            raise SyncError("%s refusé : %r traverse un dossier .git" % (what, value), EXIT_USAGE)
        # `:` en tête ouvrirait la syntaxe des pathspecs de git (`:(icase)…`, `:!…`).
        if segment.startswith(("-", ":")) or segment != segment.strip():
            raise SyncError("%s refusé : segment %r (tiret ou deux-points en tête, espace en bordure)"
                            % (what, segment), EXIT_USAGE)
        if any(ch in _FORBIDDEN or ord(ch) < 32 for ch in segment):
            raise SyncError("%s refusé : caractère non pris en charge dans %r" % (what, segment), EXIT_USAGE)
    return raw


def ensure_inside(root: str, rel: str) -> str:
    """Chemin réel sous la racine, liens symboliques résolus."""
    real_root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(real_root, rel))
    if target != real_root and not target.startswith(real_root + os.sep):
        raise SyncError("le chemin %r mène hors du dépôt" % rel, EXIT_USAGE)
    return target


def validate_branch(value, what: str = "branche") -> str:
    if not isinstance(value, str) or not value or value == "HEAD" or value.startswith("-"):
        raise SyncError("%s invalide : %r" % (what, value), EXIT_USAGE)
    if any(ch in _FORBIDDEN or ch.isspace() or ord(ch) < 32 for ch in value):
        raise SyncError("%s invalide : caractère non pris en charge dans %r" % (what, value), EXIT_USAGE)
    if git(["check-ref-format", "--branch", value], check=False).returncode != 0:
        raise SyncError("%s invalide pour git : %r" % (what, value), EXIT_USAGE)
    return value


def validate_remote(value) -> str:
    if not isinstance(value, str) or not REMOTE_RE.match(value):
        raise SyncError("nom de remote invalide : %r" % (value,), EXIT_USAGE)
    return value


def validate_slug(value, what: str = "dépôt") -> str:
    if not isinstance(value, str) or not SLUG_RE.match(value) or ".." in value:
        raise SyncError("%s invalide : %r (attendu : propriétaire/nom)" % (what, value), EXIT_USAGE)
    return value


def validate_cron(value) -> str:
    if not isinstance(value, str) or not CRON_RE.match(value.strip()):
        raise SyncError("expression cron invalide : %r (cinq champs attendus)" % (value,), EXIT_USAGE)
    return value.strip()


def validate_url(value) -> str:
    """Retourne la nature de l'URL : `https`, `ssh` ou `local`. Refuse tout identifiant embarqué."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SyncError("URL vide ou entourée d'espaces", EXIT_USAGE)
    if value.startswith("-") or any(ord(ch) < 32 for ch in value):
        raise SyncError("URL refusée : %r" % value, EXIT_USAGE)
    scheme = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*)://([^/]*)", value)
    if scheme:
        name, authority = scheme.group(1).lower(), scheme.group(2)
        if name == "https":
            if "@" in authority:
                raise SyncError("URL refusée : elle embarque un identifiant. Un jeton se range dans un "
                                "secret GitHub, jamais dans une URL ni dans .gitmodules.", EXIT_USAGE)
            return "https"
        if name == "ssh":
            if ":" in authority.split("@", 1)[0] and "@" in authority:
                raise SyncError("URL refusée : mot de passe dans l'URL SSH", EXIT_USAGE)
            return "ssh"
        if name == "file":
            return "local"
        raise SyncError("protocole refusé : %s:// (acceptés : https, ssh, file)" % name, EXIT_USAGE)
    if "::" in value:
        raise SyncError("URL refusée : transport externe (%r)" % value, EXIT_USAGE)
    if re.match(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:.+", value):
        return "ssh"
    return "local"


def url_slug(url: str):
    """`propriétaire/nom` d'une URL de forge, ou None pour un chemin local ou relatif."""
    match = (re.match(r"^(?:https|ssh)://(?:[^@/]+@)?[^/:]+(?::\d+)?/(.+?)(?:\.git)?/?$", url)
             or re.match(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:(.+?)(?:\.git)?/?$", url))
    if not match:
        return None
    slug = match.group(1)
    return slug if SLUG_RE.match(slug) else None


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "oui", "on"):
        return True
    if text in ("false", "0", "no", "non", "off"):
        return False
    raise SyncError("booléen attendu (true ou false), reçu %r" % (value,), EXIT_USAGE)


def kv_to_argv(argv, keys):
    """Accepte la syntaxe du skill (`clé=valeur`) en plus des options classiques (`--clé valeur`)."""
    out = []
    for token in argv:
        match = re.match(r"^([a-z][a-z-]*)=(.*)$", token, re.S)
        if match and match.group(1) in keys:
            # Forme collée : une valeur qui commence par un tiret reste une valeur, pas une option.
            out.append("--%s=%s" % (match.group(1), match.group(2)))
        else:
            out.append(token)
    return out


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "root"


# --------------------------------------------------------------------------- fichiers

def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise SyncError("fichier illisible : %s (%s)" % (path, exc), EXIT_USAGE)


def write_text(path: str, text: str) -> bool:
    """Écrit en LF. Retourne False si le contenu était déjà celui-là."""
    data = text.encode("utf-8")
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            if fh.read() == data:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return True


def dump_json(path: str, data) -> bool:
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def copy_file(src: str, dst: str) -> bool:
    with open(src, "rb") as fh:
        data = fh.read().replace(b"\r\n", b"\n")
    if os.path.isfile(dst):
        with open(dst, "rb") as fh:
            if fh.read() == data:
                return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as fh:
        fh.write(data)
    return True


def force_rmtree(path: str) -> None:
    """Supprime un dossier, y compris les objets git en lecture seule sous Windows."""
    def _retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    if os.path.isdir(path):
        shutil.rmtree(path, onerror=_retry)


def yaml_str(value: str) -> str:
    """Scalaire YAML entre guillemets doubles : une chaîne JSON en est une forme valide."""
    return json.dumps(value, ensure_ascii=False)


def render_template(text: str, mapping: dict) -> str:
    for key, value in mapping.items():
        text = text.replace("{{%s}}" % key, value)
    left = re.search(r"\{\{[A-Z_]+\}\}", text)
    if left:
        raise SyncError("gabarit incomplet : %s non renseigné" % left.group(0))
    return text


def templates_dir(script_file: str) -> str:
    """Les gabarits ne sont livrés qu'avec le skill, pas avec la copie déposée dans un dépôt."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(script_file))), "templates")
    if not os.path.isdir(path):
        raise SyncError("gabarits introuvables : cette commande se lance depuis le skill installé, "
                        "pas depuis la copie du script dans %s" % SYNC_DIR, EXIT_USAGE)
    return path


def read_template(script_file: str, name: str) -> str:
    with open(os.path.join(templates_dir(script_file), name), "r", encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def commit_paths(root: str, paths, message: str):
    """Commit limité aux chemins donnés. Retourne le SHA créé, ou None s'il n'y avait rien."""
    existing = [p for p in paths if os.path.lexists(os.path.join(root, p))
                or git(["ls-files", "--", p], cwd=root).stdout.strip()]
    if not existing:
        return None
    git(["add", "-A", "--"] + existing, cwd=root)
    if git(["diff", "--cached", "--quiet", "--"] + existing, cwd=root, check=False).returncode == 0:
        return None
    git(["commit", "-q", "-m", message, "--"] + existing, cwd=root, env=identity_env(root))
    return git_out(["rev-parse", "HEAD"], cwd=root)


def run_main(main) -> int:
    setup_output()
    try:
        return main(sys.argv[1:]) or EXIT_OK
    except SyncError as exc:
        error(str(exc))
        return exc.code
