"""Caracterisation des regles par ligne, par bloc et par fichier sur un corpus statique.

Chaque fichier de `corpus/` est analyse avec deux jeux de seuils (defauts et seuils bas) et deux
selections de lignes modifiees (toutes, une sur trois). Le resultat est compare au fichier de
reference `golden/rules.json`."""
from __future__ import annotations

import hashlib
import json
import os
import sys

# Regles que ces trois fonctions savent produire : le corpus doit toutes les declencher, sans quoi
# une regression passerait inapercue (voir check_coverage).
EXPECTED_RULES = frozenset({
    "BUG.STRING_IDENTITY", "BUG.PRINT_STACKTRACE", "BUG.STDOUT", "BUG.FLOAT_MONEY", "BUG.STATIC_DATEFORMAT",
    "BUG.SUPPRESS", "BUG.DISABLED_TEST", "BUG.TODO", "BUG.EMPTY_RETURN_NULL", "BUG.THREAD_SLEEP",
    "BUG.ASSERT_PROD", "BUG.CATCH_BROAD", "BUG.MUTABLE_STATIC", "BUG.EQ_NAN", "BUG.AWAIT_MISSING",
    "BUG.CATCH_SWALLOWED", "BUG.CATCH_SILENT_RETURN", "BUG.RESOURCE_LEAK",
    "CPX.LARGE_FILE", "CNV.MIXED_INDENT", "CNV.LINE_LENGTH", "CNV.WILDCARD_IMPORT", "CNV.COMMENTED_CODE",
    "CNV.TRAILING_WS", "CNV.MAGIC_NUMBER",
})


def _corpus_files(corpus: str):
    rels = []
    for base, _, names in os.walk(corpus):
        for name in names:
            rels.append(os.path.relpath(os.path.join(base, name), corpus).replace("\\", "/"))
    return sorted(rels)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _compact(finding):
    """Un constat sous forme de liste ; le correctif, long et verbeux, est reduit a une empreinte :
    un changement de texte est detecte, sans noyer le diff de la reference."""
    return [finding.rule, finding.severity, finding.category, finding.line, getattr(finding, "end_line", None),
            finding.message, _digest(finding.fix), finding.evidence, finding.symbol]


def run(engine_dir: str, corpus: str) -> dict:
    """Constats de check_lines, check_blocks et check_file pour chaque combinaison (config, lignes, fichier)."""
    sys.path.insert(0, engine_dir)
    try:
        import rules_bugs
        import rules_quality
        import source
        from config import DEFAULTS, Config
    finally:
        sys.path.remove(engine_dir)
    tight = json.loads(json.dumps(DEFAULTS))
    tight["thresholds"].update({"line_length": 60, "file_lines": 100})
    configs = {"defaut": Config(json.loads(json.dumps(DEFAULTS))), "seuils_bas": Config(tight)}

    rels = _corpus_files(corpus)
    result = {}
    for config_name, cfg in configs.items():
        for selection in ("tout", "un_tiers"):
            plain = source.load(corpus, rels)
            changed = None if selection == "tout" else {sf.path: set(range(1, sf.nb_lines + 1, 3)) for sf in plain}
            files = plain if changed is None else source.load(corpus, rels, changed_lines=changed)
            for sf in files:
                result["%s|%s|%s" % (config_name, selection, sf.path)] = {
                    "lines": [_compact(f) for f in rules_bugs.check_lines(sf)],
                    "blocks": [_compact(f) for f in rules_bugs.check_blocks(sf)],
                    "file": [_compact(f) for f in rules_quality.check_file(sf, cfg)],
                }
    return result


def check_coverage(result: dict) -> list:
    """Regles attendues que le corpus ne declenche pas."""
    seen = {finding[0] for row in result.values() for part in row.values() for finding in part}
    return sorted(EXPECTED_RULES - seen)
