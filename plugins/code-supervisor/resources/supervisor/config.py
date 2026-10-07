"""Configuration du superviseur : valeurs par defaut, puis surcharge utilisateur et projet."""
from __future__ import annotations

import fnmatch
import json
import os
import sys

# Cles de premier niveau qu'une configuration de projet ne peut pas fixer (voir _drop_untrusted_keys).
PROJECT_FORBIDDEN_KEYS = ("external_tools", "log_dir")

DEFAULTS = {
    "enabled": True,
    # Severites qui renvoient l'agent au travail. Le reste est signale sans bloquer.
    "block_on_severity": ["CRITICAL"],
    # Categories qui ne bloquent jamais, meme en CRITICAL.
    "never_block_categories": [],
    # Nombre maximal de blocages pour un meme lot de problemes avant de rendre la main.
    "max_block_rounds": 3,
    "max_files": 60,
    "max_findings_in_report": 40,
    "time_budget_seconds": 45,
    "thresholds": {
        "complexity_warn": 10,
        "complexity_critical": 15,
        "function_lines_warn": 50,
        "function_lines_critical": 80,
        "nesting": 4,
        "params": 5,
        "boolean_operators": 4,
        "line_length": 140,
        "file_lines": 800,
        "duplication_lines": 6,
        "duplication_max_reports": 8,
        "duplication_corpus_files": 400,
    },
    "exclude": [
        "**/target/**", "**/build/**", "**/out/**", "**/bin/**", "**/dist/**",
        "**/node_modules/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**",
        "**/generated/**", "**/generated-sources/**", "**/*.min.js", "**/*.bundle.js",
        "**/vendor/**", "**/third_party/**", "**/.git/**", "**/*.lock",
        "**/*.g.dart", "**/*_pb2.py", "**/*.pb.go", "**/migrations/**",
        "**/.claude/**", "**/docs/rapport-supervisor/**", "**/*.lock.json", "**/package-lock.json",
    ],
    "excluded_dirs": [
        ".git", "target", "build", "out", "bin", "dist", "node_modules", ".venv",
        "venv", "__pycache__", ".idea", ".gradle", ".mvn", "generated", "vendor",
        ".claude", ".github",
    ],
    "llm": {
        "enabled": True,
        "cli": "claude",
        "model": "sonnet",
        "timeout_seconds": 180,
        "max_diff_chars": 60000,
        "max_static_findings_in_prompt": 25,
        # Fichiers de conventions lus par le relecteur, s'ils existent.
        "convention_files": [
            "CLAUDE.md", "CONTRIBUTING.md", "AGENTS.md", ".editorconfig",
            "docs/conventions.md", "docs/CONVENTIONS.md", "CODING_STYLE.md",
        ],
    },
    # Commandes de l'outillage du projet. Vides par defaut : rien n'est lance sans
    # declaration explicite, pour ne jamais declencher de build ou de CI par surprise.
    "external_tools": [],
    "log_dir": "",          # vide = <projet>/docs/rapport-supervisor
    "quiet_paths": [],      # chemins ou le superviseur ne dit rien
}


class Config:
    def __init__(self, data: dict):
        self.data = data
        self.thresholds = data["thresholds"]
        self.excluded_dirs = set(data["excluded_dirs"])
        self._exclude = data["exclude"]

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    @property
    def llm(self) -> dict:
        return self.data["llm"]

    def is_excluded(self, rel_path: str) -> bool:
        p = rel_path.replace("\\", "/")
        for pattern in self._exclude:
            if fnmatch.fnmatch(p, pattern) or fnmatch.fnmatch("/" + p, pattern):
                return True
        parts = set(p.split("/"))
        return bool(parts & self.excluded_dirs)

    def is_quiet(self, rel_path: str) -> bool:
        p = rel_path.replace("\\", "/")
        return any(fnmatch.fnmatch(p, pat) for pat in self.data.get("quiet_paths", []))


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _drop_untrusted_keys(config: dict):
    """Retire d'une configuration de projet les cles qui designent un programme a lancer
    (`external_tools`, `llm.cli`) ou un emplacement d'ecriture (`log_dir`).

    Le depot supervise est une source non fiable (depot tiers clone) : seules la configuration
    livree avec le plugin et celle de l'utilisateur honorent ces cles. Retourne la configuration
    nettoyee et la liste des cles retirees."""
    cleaned = {k: v for k, v in config.items() if k not in PROJECT_FORBIDDEN_KEYS}
    dropped = [k for k in PROJECT_FORBIDDEN_KEYS if k in config]
    llm = cleaned.get("llm")
    if isinstance(llm, dict) and "cli" in llm:
        cleaned["llm"] = {k: v for k, v in llm.items() if k != "cli"}
        dropped.append("llm.cli")
    return cleaned, dropped


def _merge_project_config(data: dict, path: str, user_dir: str) -> dict:
    cleaned, dropped = _drop_untrusted_keys(_read_json(path))
    if dropped:
        sys.stderr.write(
            "superviseur : %s declare %s : ignore, une configuration de projet ne peut pas lancer "
            "de programme ni choisir ou ecrire les rapports. A declarer dans %s si c'est voulu.\n"
            % (path, ", ".join(dropped), os.path.join(user_dir, "supervisor.config.json")))
    return _deep_merge(data, cleaned)


def load_config(project_dir: str, user_dir: str, script_dir: str = "") -> Config:
    """Fusionne, du plus general au plus specifique :
    valeurs par defaut du code, configuration livree a cote du script (installation
    plugin), configuration utilisateur, configuration du projet (privee de ses cles sensibles)."""
    merged = DEFAULTS
    trusted = [os.path.join(user_dir, "supervisor.config.json")]
    if script_dir:
        trusted.insert(0, os.path.join(script_dir, "supervisor.config.json"))
    for path in trusted:
        if os.path.isfile(path):
            merged = _deep_merge(merged, _read_json(path))
    for path in (os.path.join(project_dir, ".claude", "supervisor.config.json"),
                 os.path.join(project_dir, ".supervisor.json")):
        if os.path.isfile(path):
            merged = _merge_project_config(merged, path, user_dir)
    return Config(merged)
