"""Complexite, taille, imbrication et conventions de forme."""
from __future__ import annotations

import re
from typing import List

from model import MAJOR, MINOR, CAT_COMPLEXITY, CAT_CONVENTION, Finding
from source import SourceFile, Function, is_python, is_structural

_DECISION = re.compile(
    r"(?<![\w.])(?:if|else\s+if|elif|for|foreach|while|case|catch|except|when|&&|\|\||\?\?|and\b|or\b)"
    r"|(?<![\w:?])\?(?!\.)|\.(?:filter|map|flatMap|anyMatch|allMatch|noneMatch)\s*\("
)
_BOOL_OPS = re.compile(r"&&|\|\||(?<![\w])and(?![\w])|(?<![\w])or(?![\w])")


def cyclomatic(body_lines) -> int:
    score = 1
    for line in body_lines:
        score += len(_DECISION.findall(line))
    return score


def max_nesting(sf: SourceFile, fn: Function) -> int:
    depth = 0
    peak = 0
    if is_python(sf.path):
        base = None
        for line in fn.body:
            if not line.strip():
                continue
            ind = len(line[:len(line) - len(line.lstrip())].expandtabs(4))
            if base is None:
                base = ind
            peak = max(peak, (ind - base) // 4)
        return peak
    for line in fn.body:
        for c in line:
            if c == "{":
                depth += 1
                peak = max(peak, depth)
            elif c == "}":
                depth = max(0, depth - 1)
    return peak


def check_functions(sf: SourceFile, functions: List[Function], cfg) -> List[Finding]:
    findings: List[Finding] = []
    t = cfg.thresholds
    for fn in functions:
        if not sf.range_changed(fn.start, fn.end):
            continue
        cc = cyclomatic(fn.body)
        length = fn.length
        nesting = max_nesting(sf, fn)
        nb_params = len(fn.params)

        if cc > t["complexity_critical"]:
            findings.append(Finding(
                rule="CPX.CYCLOMATIC_HIGH", category=CAT_COMPLEXITY, severity=MAJOR,
                message="%s a une complexite cyclomatique de %d (seuil %d) : trop de chemins d'execution pour etre testee et relue surement."
                        % (fn.qualified, cc, t["complexity_critical"]),
                fix="Extraire les blocs de decision dans des methodes nommees, remplacer les cascades de if par un polymorphisme ou une table de dispatch, et sortir les gardes en debut de methode (early return).",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start), extra={"complexite": cc},
            ))
        elif cc > t["complexity_warn"]:
            findings.append(Finding(
                rule="CPX.CYCLOMATIC", category=CAT_COMPLEXITY, severity=MINOR,
                message="%s a une complexite cyclomatique de %d (seuil souhaite %d)." % (fn.qualified, cc, t["complexity_warn"]),
                fix="Extraire une ou deux responsabilites dans des methodes dediees.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start), extra={"complexite": cc},
            ))

        if length > t["function_lines_critical"]:
            findings.append(Finding(
                rule="CPX.LONG_FUNCTION", category=CAT_COMPLEXITY, severity=MAJOR,
                message="%s fait %d lignes (seuil %d)." % (fn.qualified, length, t["function_lines_critical"]),
                fix="Decouper en etapes nommees : chaque bloc commente ou separe par une ligne vide est generalement une methode a extraire.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start), extra={"lignes": length},
            ))
        elif length > t["function_lines_warn"]:
            findings.append(Finding(
                rule="CPX.FUNCTION_SIZE", category=CAT_COMPLEXITY, severity=MINOR,
                message="%s fait %d lignes (seuil souhaite %d)." % (fn.qualified, length, t["function_lines_warn"]),
                fix="Extraire les etapes intermediaires dans des methodes au nom explicite.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start), extra={"lignes": length},
            ))

        if nesting > t["nesting"]:
            findings.append(Finding(
                rule="CPX.NESTING", category=CAT_COMPLEXITY, severity=MINOR,
                message="%s imbrique %d niveaux de blocs (seuil %d)." % (fn.qualified, nesting, t["nesting"]),
                fix="Inverser les conditions pour sortir tot (early return / continue), et extraire les boucles internes.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start),
            ))

        if nb_params > t["params"] and not sf.is_test:
            findings.append(Finding(
                rule="CPX.TOO_MANY_PARAMS", category=CAT_COMPLEXITY, severity=MINOR,
                message="%s prend %d parametres (seuil %d)." % (fn.qualified, nb_params, t["params"]),
                fix="Regrouper les parametres lies dans un objet de valeur nomme, ou utiliser un constructeur fluide.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start),
            ))

        for i, line in enumerate(fn.body):
            if len(_BOOL_OPS.findall(line)) >= t["boolean_operators"]:
                findings.append(Finding(
                    rule="CPX.CONDITION", category=CAT_COMPLEXITY, severity=MINOR,
                    message="Condition composee de %d operateurs booleens dans %s." % (len(_BOOL_OPS.findall(line)), fn.qualified),
                    fix="Nommer les sous-conditions dans des variables ou des methodes booleennes (isEligible, hasQuota) pour rendre l'intention lisible.",
                    file=sf.path, line=fn.start + 1 + i, symbol=fn.qualified,
                    evidence=sf.snippet(fn.start + 1 + i),
                ))
                break
    return findings


_IMPORT_WILDCARD = re.compile(r"^\s*import\s+[\w.]+\.\*\s*;|^\s*from\s+[\w.]+\s+import\s+\*")
_COMMENTED_CODE = re.compile(r"^\s*(?://|#)\s*(?:[\w.\[\]]+\s*=|if\s*\(|for\s*\(|while\s*\(|return\b|"
                             r"public\s|private\s|def\s|}\s*$|\w+\([^)]*\)\s*;)")
_POWERS = {"16", "32", "64", "128", "256", "512", "1024", "2048", "4096", "8192",
           "16384", "32768", "65536", "1048576"}
_MAGIC = re.compile(r"(?<![\w.\"'])(?!0|1|2|10|100|1000)(\d{2,})(?![\w.\"'])")
_CONST_CTX = re.compile(r"(?i)(?:final|const|static|#define|enum|version|port|timeout|http|status)")


_INDENT_SCAN_LINES = 400          # lignes examinees pour detecter une indentation mixte
_MAX_MAGIC_NUMBERS_PER_FILE = 5   # au-dela, le fichier est signale ailleurs : inutile d'inonder le rapport
_EVIDENCE_WIDTH = 120
_MAGIC_EXCLUDED_CONTEXT = re.compile(r"(?i)(?:line|version|\.\d|uuid|sql|select)")


def _file_findings(sf: SourceFile, thresholds) -> List[Finding]:
    """Constats portant sur le fichier entier : taille et indentation."""
    findings: List[Finding] = []
    if sf.nb_lines > thresholds["file_lines"]:
        findings.append(Finding(
            rule="CPX.LARGE_FILE", category=CAT_COMPLEXITY, severity=MINOR,
            message="%s fait %d lignes (seuil %d) : le fichier porte probablement plusieurs responsabilites."
                    % (sf.path, sf.nb_lines, thresholds["file_lines"]),
            fix="Extraire les responsabilites secondaires dans des classes ou modules dedies.",
            file=sf.path, line=1,
        ))
    head = sf.lines[:_INDENT_SCAN_LINES]
    if any("\t" in l for l in head) and any(l.startswith("    ") for l in head):
        findings.append(Finding(
            rule="CNV.MIXED_INDENT", category=CAT_CONVENTION, severity=MINOR,
            message="Indentation mixte tabulations / espaces dans le fichier.",
            fix="Aligner l'indentation sur celle du reste du depot (voir .editorconfig s'il existe).",
            file=sf.path, line=1,
        ))
    return findings


def _convention(sf: SourceFile, idx: int, rule: str, message: str, fix: str, evidence: str = "") -> Finding:
    return Finding(rule=rule, category=CAT_CONVENTION, severity=MINOR, message=message, fix=fix,
                   file=sf.path, line=idx, evidence=evidence)


def _form_findings(sf: SourceFile, idx: int, raw: str, max_line_length: int) -> List[Finding]:
    """Conventions de forme d'une ligne : longueur, import generique, code commente, espaces de fin."""
    findings: List[Finding] = []
    shown = raw.strip()[:_EVIDENCE_WIDTH]
    if len(raw) > max_line_length:
        findings.append(_convention(
            sf, idx, "CNV.LINE_LENGTH", "Ligne de %d caracteres (seuil %d)." % (len(raw), max_line_length),
            "Couper la ligne ou extraire une variable intermediaire nommee.", shown))
    if _IMPORT_WILDCARD.match(raw):
        findings.append(_convention(
            sf, idx, "CNV.WILDCARD_IMPORT",
            "Import generique (*) : masque l'origine des symboles et provoque des collisions.",
            "Importer explicitement les types utilises.", shown))
    if _COMMENTED_CODE.match(raw):
        findings.append(_convention(
            sf, idx, "CNV.COMMENTED_CODE", "Code commente laisse en place.",
            "Supprimer le code mort : l'historique git le conserve si besoin.", shown))
    if raw.rstrip() != raw and raw.strip():
        findings.append(_convention(
            sf, idx, "CNV.TRAILING_WS", "Espaces en fin de ligne.",
            "Supprimer les espaces de fin (la plupart des formateurs le font automatiquement)."))
    return findings


def _magic_number_finding(sf: SourceFile, idx: int, clean: str):
    # Les valeurs d'un fichier de configuration (yaml, json, xml) sont des donnees, pas du code.
    if sf.is_test or not is_structural(sf.path) or _CONST_CTX.search(clean):
        return None
    match = _MAGIC.search(clean)
    if not match or match.group(1) in _POWERS or _MAGIC_EXCLUDED_CONTEXT.search(clean):
        return None
    return _convention(
        sf, idx, "CNV.MAGIC_NUMBER", "Valeur numerique %s utilisee directement, sans nom." % match.group(1),
        "Extraire la valeur dans une constante nommee qui explique ce qu'elle represente et son unite.",
        clean.strip()[:_EVIDENCE_WIDTH])


def check_file(sf: SourceFile, cfg) -> List[Finding]:
    thresholds = cfg.thresholds
    findings = _file_findings(sf, thresholds)
    magic_count = 0
    for idx, raw in enumerate(sf.lines, start=1):
        if not sf.is_changed(idx):
            continue
        clean = sf.clean_lines[idx - 1] if idx - 1 < len(sf.clean_lines) else ""
        findings.extend(_form_findings(sf, idx, raw, thresholds["line_length"]))
        if magic_count >= _MAX_MAGIC_NUMBERS_PER_FILE:
            continue
        magic = _magic_number_finding(sf, idx, clean)
        if magic:
            findings.append(magic)
            magic_count += 1
    return findings


def check_unused_imports(sf: SourceFile) -> List[Finding]:
    """Imports Java/Python non references ailleurs dans le fichier."""
    findings: List[Finding] = []
    body = "\n".join(l for l in sf.clean_lines if not re.match(r"^\s*import\s", l))
    for idx, raw in enumerate(sf.lines, start=1):
        if not sf.is_changed(idx):
            continue
        m = re.match(r"^\s*import\s+(?:static\s+)?([\w.]+)(?:\s*;)?\s*$", raw)
        if not m or m.group(1).endswith("*"):
            continue
        simple = m.group(1).rsplit(".", 1)[-1]
        if len(simple) < 2:
            continue
        occurrences = len(re.findall(r"(?<![\w])%s(?![\w])" % re.escape(simple), body))
        if occurrences == 0:
            findings.append(Finding(
                rule="CNV.UNUSED_IMPORT", category=CAT_CONVENTION, severity=MINOR,
                message="Import %s inutilise." % m.group(1),
                fix="Supprimer l'import.",
                file=sf.path, line=idx, evidence=raw.strip()[:120],
            ))
    return findings
