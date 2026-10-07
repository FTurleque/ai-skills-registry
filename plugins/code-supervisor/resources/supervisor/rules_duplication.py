"""Detection de duplication de code par hachage de fenetres de lignes normalisees."""
from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from model import MAJOR, MINOR, CAT_DUPLICATION, Finding
from source import SourceFile, load, is_structural, scrub

_WS = re.compile(r"\s+")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_NOISE = re.compile(r"^[\s{}();,\]\[]*$")
# Entetes, imports et annotations : identiques partout, sans valeur pour la duplication.
_HEADER = re.compile(r"^\s*(?:package|import|using|#include|from\s+[\w.]+\s+import|@[A-Z]\w*|"
                     r"public\s+(?:final\s+)?(?:class|interface|enum|record)|namespace)\b")
# Declaration de champ seule (`private final X y;`) : de la forme, sans logique. Deux classes qui declarent des
# champs de meme forme ne se dupliquent pas.
_FIELD_DECLARATION = re.compile(
    r"^(?:(?:public|private|protected|static|final|volatile|transient)\s+)+[\w<>\[\],.? ]+\s+v;?$")
_KEYWORDS = {
    "if", "else", "for", "while", "return", "new", "public", "private", "protected",
    "static", "final", "void", "try", "catch", "finally", "throw", "throws", "class",
    "import", "package", "def", "self", "this", "const", "let", "var", "function",
    "switch", "case", "break", "continue", "true", "false", "null", "none", "in", "not",
    "and", "or", "int", "long", "double", "float", "boolean", "string", "list", "map",
}


def normalize(line: str) -> str:
    """Neutralise les identifiants et les litteraux pour comparer la structure."""
    s = line.strip()
    if not s or _NOISE.match(s) or _HEADER.match(s):
        return ""
    s = _NUM.sub("0", s)
    def repl(m):
        w = m.group(0)
        return w if w.lower() in _KEYWORDS else "v"
    s = _IDENT.sub(repl, s)
    s = _WS.sub(" ", s)
    return "" if _FIELD_DECLARATION.match(s) else s


def fingerprints(sf: SourceFile, window: int) -> List[Tuple[str, int, int]]:
    """Retourne (hash, ligne de debut, ligne de fin) pour chaque fenetre significative."""
    norm = []
    for i, line in enumerate(sf.clean_lines, start=1):
        n = normalize(line)
        if n and len(n) >= 8:
            norm.append((i, n))
    out = []
    for i in range(0, max(0, len(norm) - window + 1)):
        chunk = norm[i:i + window]
        blob = "\n".join(c[1] for c in chunk)
        h = hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()[:16]
        out.append((h, chunk[0][0], chunk[-1][0]))
    return out


Location = Tuple[str, int, int]    # (chemin, ligne de debut, ligne de fin)
_REFERENCE_MAX_BYTES = 300000      # taille maximale d'un fichier de reference lu


def _target_files(changed: List[SourceFile]) -> List[SourceFile]:
    """Fichiers modifies que l'on compare : du code (pas de la configuration) qui n'est pas un test."""
    return [sf for sf in changed if is_structural(sf.path) and not sf.is_test]


def _duplicated_pair(locs: List[Location], changed_paths) -> Optional[Tuple[Location, Location]]:
    """(emplacement dans un fichier modifie, autre emplacement du meme bloc), ou None."""
    inside = [loc for loc in locs if loc[0] in changed_paths]
    if not inside:
        return None
    first = inside[0]
    other = next((loc for loc in locs if loc != first), None)
    return None if other is None else (first, other)


def _duplicate_finding(first: Location, other: Location, window: int) -> Finding:
    same_file = first[0] == other[0]
    return Finding(
        rule="DUP.BLOCK", category=CAT_DUPLICATION,
        severity=MAJOR if not same_file else MINOR,
        message="Bloc de %d lignes duplique : %s:%d-%d reprend %s:%d-%d."
                % (window, first[0], first[1], first[2], other[0], other[1], other[2]),
        fix=("Extraire le bloc commun dans une methode ou une classe partagee et l'appeler depuis les deux endroits. "
             "Si le code existait deja ailleurs, reutiliser l'implementation existante au lieu d'en ecrire une seconde."),
        file=first[0], line=first[1], end_line=first[2],
        extra={"duplique_avec": "%s:%d-%d" % other},
    )


def _report(index: Dict[str, List[Location]], changed_paths, window: int, max_reports: int) -> List[Finding]:
    findings: List[Finding] = []
    reported = set()
    for locs in index.values():
        if len(locs) < 2:
            continue
        pair = _duplicated_pair(locs, changed_paths)
        if pair is None:
            continue
        first, other = pair
        marker = (first[0], first[1] // max(window, 1))   # des fenetres voisines ne font qu'un seul constat
        if marker in reported:
            continue
        reported.add(marker)
        findings.append(_duplicate_finding(first, other, window))
        if len(findings) >= max_reports:
            break
    return findings


def check(changed: List[SourceFile], root: str, cfg) -> List[Finding]:
    window = cfg.thresholds["duplication_lines"]
    targets = _target_files(changed)
    if not targets:
        return []

    index: Dict[str, List[Location]] = defaultdict(list)
    for sf in targets:
        for h, start, end in fingerprints(sf, window):
            index[h].append((sf.path, start, end))

    # Reference : le reste du depot, pour reperer une reimplementation d'un code existant.
    for sf in _corpus_files(root, targets, cfg):
        for h, start, end in fingerprints(sf, window):
            if h in index:
                index[h].append((sf.path, start, end))

    return _report(index, {sf.path for sf in targets}, window, cfg.thresholds["duplication_max_reports"])


def _reference_path(root: str, dirpath: str, filename: str, extensions, target_paths, cfg) -> Optional[str]:
    """Chemin relatif d'un fichier de reference, ou None : autre extension, fichier modifie, ou exclu."""
    if os.path.splitext(filename)[1].lower() not in extensions:
        return None
    rel = os.path.relpath(os.path.join(dirpath, filename), root).replace("\\", "/")
    if rel in target_paths or cfg.is_excluded(rel):
        return None
    return rel


def _collect_candidates(root: str, base: str, extensions, target_paths, cfg, candidates: List[str], limit: int) -> None:
    """Ajoute a `candidates` les fichiers de reference sous `base`, dans l'ordre du parcours, jusqu'a `limit`."""
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in cfg.excluded_dirs]
        for filename in filenames:
            rel = _reference_path(root, dirpath, filename, extensions, target_paths, cfg)
            if rel is None:
                continue
            candidates.append(rel)
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break


def _corpus_files(root: str, targets: List[SourceFile], cfg) -> List[SourceFile]:
    """Echantillon du depot limite en nombre de fichiers, pour tenir le budget de temps."""
    extensions = {os.path.splitext(sf.path)[1].lower() for sf in targets}
    target_paths = {sf.path for sf in targets}
    limit = cfg.thresholds["duplication_corpus_files"]
    candidates: List[str] = []
    for top in sorted({sf.path.split("/")[0] for sf in targets}):
        base = os.path.join(root, top) if top else root
        if not os.path.isdir(base):
            continue
        _collect_candidates(root, base, extensions, target_paths, cfg, candidates, limit)
        if len(candidates) >= limit:
            break
    return load(root, candidates, max_bytes=_REFERENCE_MAX_BYTES)
