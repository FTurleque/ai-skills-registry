"""Regles evaluees ligne par ligne : parcours commun aux regles de bugs et de securite.

Un jeu de regles (`LineRules`) dit quels motifs appliquer et comment lire la ligne ; les modules de regles
n'y ajoutent que ce qui leur est propre : la categorie, la gravite et les exceptions."""
from __future__ import annotations

from typing import Callable, List, NamedTuple, Tuple

from model import Finding
from source import SourceFile

EVIDENCE_WIDTH = 200       # longueur maximale de l'extrait de code joint au constat

# (id, langages ou None, motif, gravite, message, correctif)
Pattern = Tuple[str, object, object, str, str, str]


class LineRules(NamedTuple):
    patterns: List[Pattern]
    raw_rules: Tuple[str, ...]     # regles lues sur la ligne brute (le contenu des litteraux compte) ;
                                   # les autres se lisent sur la ligne nettoyee (commentaires et chaines ignores)
    category: Callable[[str], str]                       # id de regle -> categorie
    severity: Callable[[SourceFile, str, str], str]      # (fichier, id, gravite du motif) -> gravite retenue
    is_excluded: Callable[..., bool]                     # (fichier, id, correspondance, brut, nettoye, epure) -> bool


def line_findings(rules: LineRules, sf: SourceFile, idx: int, raw: str, clean: str, stripped: str) -> List[Finding]:
    findings: List[Finding] = []
    for rule_id, langs, rx, severity, message, fix in rules.patterns:
        if langs and sf.lang not in langs:
            continue
        match = rx.search(raw if rule_id in rules.raw_rules else clean)
        if not match or rules.is_excluded(sf, rule_id, match, raw, clean, stripped):
            continue
        findings.append(Finding(
            rule=rule_id, category=rules.category(rule_id), severity=rules.severity(sf, rule_id, severity),
            message=message, fix=fix, file=sf.path, line=idx, evidence=stripped[:EVIDENCE_WIDTH],
        ))
    return findings
