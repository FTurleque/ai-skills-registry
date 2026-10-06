"""Detection de duplication de code par hachage de fenetres de lignes normalisees."""
from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from model import MAJOR, MINOR, CAT_DUPLICATION, Finding
from source import SourceFile, load, is_structural, scrub

_WS = re.compile(r"\s+")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_NOISE = re.compile(r"^[\s{}();,\]\[]*$")
# Entetes, imports et annotations : identiques partout, sans valeur pour la duplication.
_HEADER = re.compile(r"^\s*(?:package|import|using|#include|from\s+[\w.]+\s+import|@[A-Z]\w*|"
                     r"public\s+(?:final\s+)?(?:class|interface|enum|record)|namespace)\b")
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
    return s


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


def check(changed: List[SourceFile], root: str, cfg) -> List[Finding]:
    window = cfg.thresholds["duplication_lines"]
    findings: List[Finding] = []
    index: Dict[str, List[Tuple[str, int, int]]] = defaultdict(list)

    targets = [sf for sf in changed if is_structural(sf.path) and not sf.is_test]
    if not targets:
        return findings

    for sf in targets:
        for h, start, end in fingerprints(sf, window):
            index[h].append((sf.path, start, end))

    # Reference : le reste du depot, pour reperer une reimplementation d'un code existant.
    corpus = _corpus_files(root, targets, cfg)
    for sf in corpus:
        for h, start, end in fingerprints(sf, window):
            if h in index:
                index[h].append((sf.path, start, end))

    reported = set()
    changed_paths = {sf.path for sf in targets}
    for h, locs in index.items():
        if len(locs) < 2:
            continue
        inside = [l for l in locs if l[0] in changed_paths]
        if not inside:
            continue
        first = inside[0]
        other = next((l for l in locs if l != first), None)
        if other is None:
            continue
        marker = (first[0], first[1] // max(window, 1))
        if marker in reported:
            continue
        reported.add(marker)
        same_file = first[0] == other[0]
        findings.append(Finding(
            rule="DUP.BLOCK", category=CAT_DUPLICATION,
            severity=MAJOR if not same_file else MINOR,
            message="Bloc de %d lignes duplique : %s:%d-%d reprend %s:%d-%d."
                    % (window, first[0], first[1], first[2], other[0], other[1], other[2]),
            fix=("Extraire le bloc commun dans une methode ou une classe partagee et l'appeler depuis les deux endroits. "
                 "Si le code existait deja ailleurs, reutiliser l'implementation existante au lieu d'en ecrire une seconde."),
            file=first[0], line=first[1], end_line=first[2],
            extra={"duplique_avec": "%s:%d-%d" % other},
        ))
        if len(findings) >= cfg.thresholds["duplication_max_reports"]:
            break
    return findings


def _corpus_files(root: str, targets: List[SourceFile], cfg) -> List[SourceFile]:
    """Echantillon du depot limite en nombre de fichiers, pour tenir le budget de temps."""
    exts = {os.path.splitext(sf.path)[1].lower() for sf in targets}
    target_paths = {sf.path for sf in targets}
    roots = sorted({sf.path.split("/")[0] for sf in targets})
    candidates = []
    limit = cfg.thresholds["duplication_corpus_files"]
    for top in roots:
        base = os.path.join(root, top) if top else root
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in cfg.excluded_dirs]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in exts:
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
                if rel in target_paths or cfg.is_excluded(rel):
                    continue
                candidates.append(rel)
                if len(candidates) >= limit:
                    break
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break
    return load(root, candidates, max_bytes=300000)
