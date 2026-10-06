"""Regles de detection de bugs probablement introduits par la modification."""
from __future__ import annotations

import re
from typing import List

from model import CRITICAL, MAJOR, MINOR, CAT_BUG, CAT_CONVENTION, Finding
from source import SourceFile, Function, is_c_family, is_python, is_structural

LINE_PATTERNS = [
    ("BUG.STRING_IDENTITY", ("java", "kotlin", "csharp", "scala"), re.compile(
        r"(?:[\w.)\]]+\s*[!=]=\s*\"|\"\s*[!=]=\s*[\w.(\[])"), MAJOR,
     "Comparaison de chaines avec == / != : compare les references, pas le contenu.",
     "Utiliser equals (ou Objects.equals pour tolerer null, ou equalsIgnoreCase si la casse est indifferente)."),
    ("BUG.PRINT_STACKTRACE", None, re.compile(r"\.printStackTrace\s*\(\s*\)"), MAJOR,
     "Exception ecrite sur la sortie standard : elle echappe au systeme de journalisation.",
     "Journaliser via le logger avec le contexte metier (logger.error(\"...\", e)) ou propager l'exception."),
    ("BUG.STDOUT", None, re.compile(
        r"(?:System\.(?:out|err)\.print(?:ln)?\s*\(|(?<![\w.])console\.(?:log|debug)\s*\(|^\s*print\s*\()"), MINOR,
     "Ecriture sur la sortie standard dans du code de production.",
     "Remplacer par un appel au logger au niveau approprie, ou supprimer si c'etait une trace de mise au point."),
    ("BUG.FLOAT_MONEY", None, re.compile(
        r"(?i)\b(?:float|double)\s+\w*(?:price|amount|montant|total|balance|solde|cost|cout|tax|tva|salary|fee)\w*\s*[=;)]"), MAJOR,
     "Montant monetaire stocke en float/double : erreurs d'arrondi garanties.",
     "Utiliser BigDecimal (ou un entier de centimes) pour tout calcul monetaire."),
    ("BUG.STATIC_DATEFORMAT", ("java",), re.compile(
        r"static\s+(?:final\s+)?(?:SimpleDateFormat|DateFormat|NumberFormat|DecimalFormat)\b"), MAJOR,
     "Formateur de date/nombre partage en statique : ces classes ne sont pas thread-safe.",
     "Utiliser DateTimeFormatter (immuable) ou instancier le formateur localement a chaque usage."),
    ("BUG.SUPPRESS", None, re.compile(
        r"(?i)(?://\s*NOSONAR|@SuppressWarnings|#\s*noqa|//\s*eslint-disable|#\s*type:\s*ignore|"
        r"@ts-ignore|@ts-nocheck|//\s*skipcq|@SuppressFBWarnings)"), MAJOR,
     "Avertissement de l'outillage qualite neutralise.",
     "Corriger la cause de l'avertissement ; si la suppression est justifiee, la restreindre a la regle precise et ajouter un commentaire expliquant pourquoi."),
    ("BUG.DISABLED_TEST", None, re.compile(
        r"(?i)(?:@Disabled|@Ignore|\.skip\s*\(|xit\s*\(|xdescribe\s*\(|@(?:pytest\.mark\.)?skip\b|@Test\s*\(\s*enabled\s*=\s*false)"), MAJOR,
     "Test desactive.",
     "Reactiver le test et corriger le code sous-jacent ; si la desactivation est volontaire, documenter la raison et la date de reactivation."),
    ("BUG.TODO", None, re.compile(r"(?://|#|/\*|\*)\s*(?:TODO|FIXME|XXX|HACK|BUG)\b"), MINOR,
     "Marqueur TODO/FIXME laisse dans le code.",
     "Traiter le point maintenant, ou le sortir du code vers le suivi des taches avec une reference."),
    ("BUG.EMPTY_RETURN_NULL", None, re.compile(r"return\s+null\s*;"), MINOR,
     "Retour de null.",
     "Pour une collection, retourner une collection vide ; sinon preferer Optional ou lever une exception explicite."),
    ("BUG.THREAD_SLEEP", None, re.compile(r"(?:Thread\.sleep\s*\(|time\.sleep\s*\(|setTimeout\s*\([^,]+,\s*\d{4,})"), MINOR,
     "Attente par pause fixe.",
     "Attendre une condition (await / polling avec condition et delai maximum) plutot qu'une duree arbitraire."),
    ("BUG.ASSERT_PROD", ("java", "python"), re.compile(r"^\s*assert\s+"), MINOR,
     "Validation par assert dans du code de production : les assertions peuvent etre desactivees a l'execution.",
     "Remplacer par une verification explicite levant une exception (IllegalArgumentException, ValueError)."),
    ("BUG.CATCH_BROAD", None, re.compile(
        r"catch\s*\(\s*(?:final\s+)?(?:Exception|Throwable|RuntimeException|Error)\s|except\s*(?:BaseException|Exception)?\s*:"), MINOR,
     "Capture d'exception trop large.",
     "Capturer les types d'exception reellement attendus ; si la capture large est voulue, journaliser et renvoyer une exception metier."),
    ("BUG.MUTABLE_STATIC", ("java",), re.compile(
        r"(?:public|protected)\s+static\s+(?!final)[\w<>,\[\]]+\s+\w+\s*(?:=|;)"), MAJOR,
     "Etat statique mutable expose : source de fuites et de problemes de concurrence.",
     "Rendre le champ final et immuable, ou l'encapsuler derriere un accesseur controle."),
    ("BUG.EQ_NAN", None, re.compile(r"[!=]=\s*(?:Double|Float)\.NaN|[!=]=\s*NaN\b"), MAJOR,
     "Comparaison a NaN : toujours fausse.",
     "Utiliser Double.isNaN(x) / Number.isNaN(x)."),
    ("BUG.AWAIT_MISSING", ("js", "ts"), re.compile(
        r"(?<![\w.])(?:fetch|axios\.(?:get|post|put|delete)|\w+Async)\s*\([^;]*\)\s*;\s*$"), MINOR,
     "Appel asynchrone dont la promesse n'est ni attendue ni chainee : erreurs silencieuses.",
     "Ajouter await, ou chainer .then/.catch, ou retourner la promesse a l'appelant."),
]


def _is_real_suppression(rx, raw: str, clean: str) -> bool:
    """Vrai si un marqueur de suppression se trouve dans du code ou un commentaire.

    `clean` neutralise les litteraux (« _ ») en gardant la geometrie de la ligne : un marqueur
    cite dans une chaine ou dans une regle de documentation n'est pas une suppression."""
    return any(m.start() >= len(clean) or clean[m.start()] != "_" for m in rx.finditer(raw))


_RAW_TEXT_RULES = ("BUG.TODO", "BUG.SUPPRESS")                  # marqueurs qui vivent dans les commentaires
_CONVENTION_RULES = ("BUG.TODO", "BUG.SUPPRESS", "BUG.STDOUT")
_SEVERE_IN_TESTS = ("BUG.DISABLED_TEST", "BUG.SUPPRESS")         # gardent leur severite dans les tests
_PYTHON_COMMENT_OR_MAIN = re.compile(r"^\s*(?:#|if\s+__name__)")
_PYTHON_PRINT = re.compile(r"(?<![\w.])print\s*\(")
_EMPTY_STRING_COMPARISON = re.compile(r"(?:\"\"|'')\s*[!=]=")
_ENTRY_POINT_SUFFIXES = ("Main.java", "__main__.py")


def _skip_stdout(sf, raw, clean, stripped, rx) -> bool:
    if sf.is_test or (sf.lang == "python" and _PYTHON_COMMENT_OR_MAIN.match(stripped)):
        return True
    if sf.lang == "python" and not _PYTHON_PRINT.search(clean):
        return True
    return "/cli/" in sf.path or "/scripts/" in sf.path or sf.path.endswith(_ENTRY_POINT_SUFFIXES)


def _skip_suppress(sf, raw, clean, stripped, rx) -> bool:
    return not (is_structural(sf.path) and _is_real_suppression(rx, raw, clean))


def _skip_outside_tests(sf, raw, clean, stripped, rx) -> bool:
    return not sf.is_test


def _skip_in_tests(sf, raw, clean, stripped, rx) -> bool:
    return sf.is_test


def _skip_empty_string_comparison(sf, raw, clean, stripped, rx) -> bool:
    return bool(_EMPTY_STRING_COMPARISON.search(clean))


# Exceptions propres a une regle : si le predicat est vrai, la ligne n'est pas signalee.
_SKIP_WHEN = {
    "BUG.STDOUT": _skip_stdout,
    "BUG.SUPPRESS": _skip_suppress,
    "BUG.DISABLED_TEST": _skip_outside_tests,
    "BUG.ASSERT_PROD": _skip_in_tests,
    "BUG.STRING_IDENTITY": _skip_empty_string_comparison,
    "BUG.EMPTY_RETURN_NULL": _skip_in_tests,
}


def _line_severity(sf: SourceFile, rule_id: str, severity: str) -> str:
    if sf.is_test and severity == MAJOR and rule_id not in _SEVERE_IN_TESTS:
        return MINOR
    return severity


def _line_findings(sf: SourceFile, idx: int, raw: str, clean: str, stripped: str) -> List[Finding]:
    findings: List[Finding] = []
    for rule_id, langs, rx, severity, message, fix in LINE_PATTERNS:
        if langs and sf.lang not in langs:
            continue
        if not rx.search(raw if rule_id in _RAW_TEXT_RULES else clean):
            continue
        skip = _SKIP_WHEN.get(rule_id)
        if skip and skip(sf, raw, clean, stripped, rx):
            continue
        findings.append(Finding(
            rule=rule_id, category=CAT_CONVENTION if rule_id in _CONVENTION_RULES else CAT_BUG,
            severity=_line_severity(sf, rule_id, severity), message=message, fix=fix,
            file=sf.path, line=idx, evidence=stripped[:200],
        ))
    return findings


def check_lines(sf: SourceFile) -> List[Finding]:
    findings: List[Finding] = []
    for idx, raw in enumerate(sf.lines, start=1):
        stripped = raw.strip()
        if not stripped or not sf.is_changed(idx):
            continue
        clean = sf.clean_lines[idx - 1] if idx - 1 < len(sf.clean_lines) else ""
        findings.extend(_line_findings(sf, idx, raw, clean, stripped))
    return findings


_CATCH = re.compile(r"catch\s*\(([^)]*)\)\s*\{")
_PY_EXCEPT = re.compile(r"^(\s*)except\b[^:]*:\s*$")
_RESOURCES = re.compile(
    r"new\s+(?:FileInputStream|FileOutputStream|FileReader|FileWriter|RandomAccessFile|Socket|"
    r"ServerSocket|Scanner|BufferedReader|BufferedWriter|PrintWriter|ObjectOutputStream|"
    r"ObjectInputStream|ZipFile|JarFile)\s*\(|Files\.(?:newInputStream|newOutputStream|newBufferedReader|"
    r"newBufferedWriter|lines|walk|list)\s*\(|\.getConnection\s*\(|\.createStatement\s*\(")


_DOCUMENTED_MIN_CHARS = 25     # longueur d'un commentaire qui justifie un bloc catch vide
_SWALLOWING_STATEMENTS = ("pass", "...", "continue")


def _catch_findings(sf: SourceFile, clean, i: int, match) -> List[Finding]:
    body, closing = _brace_body(clean, i, match.end(0) - 1)
    if _is_empty_body(body):
        # Un bloc vide mais commente est une decision assumee : on signale sans bloquer.
        documented = len(_comment_in(sf, i + 1, closing + 1)) >= _DOCUMENTED_MIN_CHARS
        return [Finding(
            rule="BUG.CATCH_SWALLOWED", category=CAT_BUG,
            severity=MINOR if documented else CRITICAL,
            message=("Exception capturee et ignoree, avec justification en commentaire."
                     if documented else
                     "Exception capturee puis ignoree : l'erreur disparait sans trace."),
            fix=("Verifier que l'absence de journalisation est toujours justifiee."
                 if documented else
                 "Journaliser l'exception avec son contexte, ou la propager ; un bloc catch vide n'est acceptable qu'avec un commentaire expliquant pourquoi l'erreur peut etre ignoree."),
            file=sf.path, line=i + 1, end_line=closing + 1,
            evidence=sf.snippet(i + 1), symbol=match.group(1).strip()[:60],
        )]
    if len(body) <= 2 and any(re.search(r"(?i)^\s*(?:return|break|continue)\b", b) for b in body) \
            and not any(re.search(r"(?i)log|throw|raise|print", b) for b in body):
        return [Finding(
            rule="BUG.CATCH_SILENT_RETURN", category=CAT_BUG, severity=MAJOR,
            message="Exception capturee et transformee en sortie silencieuse.",
            fix="Journaliser la cause avant de sortir, ou renvoyer une erreur metier explicite a l'appelant.",
            file=sf.path, line=i + 1, end_line=closing + 1, evidence=sf.snippet(i + 1),
        )]
    return []


def _resource_leak_finding(sf: SourceFile, clean, i: int):
    if not _RESOURCES.search(clean[i]) or sf.is_test:
        return None
    window = " ".join(clean[max(0, i - 2):i + 1])
    if "try" in window or ".close()" in " ".join(clean[i:i + 25]) or "return" in clean[i]:
        return None
    return Finding(
        rule="BUG.RESOURCE_LEAK", category=CAT_BUG, severity=MAJOR,
        message="Ressource ouverte sans fermeture garantie.",
        fix="Ouvrir la ressource dans un try-with-resources (Java) ou un bloc equivalent qui ferme meme en cas d'exception.",
        file=sf.path, line=i + 1, evidence=sf.snippet(i + 1),
    )


def _c_family_blocks(sf: SourceFile) -> List[Finding]:
    clean = sf.clean_lines
    findings: List[Finding] = []
    for i in range(len(clean)):
        if not sf.is_changed(i + 1):
            continue
        match = _CATCH.search(clean[i])
        if match:
            findings.extend(_catch_findings(sf, clean, i, match))
        leak = _resource_leak_finding(sf, clean, i)
        if leak:
            findings.append(leak)
    return findings


def _except_body(clean, i: int, indent: int) -> List[str]:
    """Instructions du bloc `except` ouvert a la ligne i, indentees plus que lui."""
    body = []
    for j in range(i + 1, len(clean)):
        if not clean[j].strip():
            continue
        j_indent = len(clean[j][:len(clean[j]) - len(clean[j].lstrip())].expandtabs(4))
        if j_indent <= indent:
            break
        body.append(clean[j].strip())
    return body


def _python_except_blocks(sf: SourceFile) -> List[Finding]:
    clean = sf.clean_lines
    findings: List[Finding] = []
    for i in range(len(clean)):
        if not sf.is_changed(i + 1):
            continue
        match = _PY_EXCEPT.match(clean[i])
        if not match:
            continue
        body = _except_body(clean, i, len(match.group(1).expandtabs(4)))
        if body and all(b in _SWALLOWING_STATEMENTS or b.startswith("#") for b in body):
            findings.append(Finding(
                rule="BUG.CATCH_SWALLOWED", category=CAT_BUG, severity=CRITICAL,
                message="Exception capturee puis ignoree (pass) : l'erreur disparait sans trace.",
                fix="Journaliser l'exception (logger.exception) ou la propager ; preciser aussi le type attendu au lieu d'un except nu.",
                file=sf.path, line=i + 1, evidence=sf.snippet(i + 1),
            ))
    return findings


def check_blocks(sf: SourceFile) -> List[Finding]:
    """Controles necessitant plusieurs lignes de contexte."""
    findings: List[Finding] = []
    if is_c_family(sf.path):
        findings.extend(_c_family_blocks(sf))
    if is_python(sf.path):
        findings.extend(_python_except_blocks(sf))
    return findings


def _brace_body(lines, start_line: int, brace_col: int):
    """Retourne (lignes du corps, index de la ligne fermante)."""
    depth = 0
    body = []
    for i in range(start_line, min(len(lines), start_line + 400)):
        line = lines[i]
        begin = brace_col if i == start_line else 0
        for col in range(begin, len(line)):
            c = line[col]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return body, i
        if i > start_line or depth > 0:
            segment = line if i != start_line else line[brace_col + 1:]
            if segment.strip():
                body.append(segment.strip())
    return body, min(len(lines) - 1, start_line)


def _comment_in(sf, start: int, end: int) -> str:
    """Texte des commentaires presents entre deux lignes (1-indexe)."""
    out = []
    for i in range(start, min(end + 1, len(sf.lines) + 1)):
        raw = sf.lines[i - 1].strip()
        m = re.search(r"(?://|/\*|\*|#)\s*(.+)$", raw)
        if m and sf.clean_lines[i - 1].strip() in ("", "{", "}", "} {"):
            out.append(m.group(1).strip(" */"))
    return " ".join(out)


def _is_empty_body(body) -> bool:
    return all((not b) or b in ("{", "}") for b in body)


def check_function_bugs(sf: SourceFile, functions: List[Function]) -> List[Finding]:
    findings: List[Finding] = []
    for fn in functions:
        if not sf.range_changed(fn.start, fn.end):
            continue
        body = "\n".join(fn.body)
        # Optional.get sans verification
        if re.search(r"\.get\s*\(\s*\)", body) and "Optional" in body and \
                not re.search(r"isPresent|isEmpty|orElse|ifPresent|orElseThrow", body):
            findings.append(Finding(
                rule="BUG.OPTIONAL_GET", category=CAT_BUG, severity=MAJOR,
                message="Optional.get() appele sans verifier la presence de valeur.",
                fix="Utiliser orElseThrow avec un message explicite, orElse, ou ifPresent.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start),
            ))
        # boucle qui modifie la collection iteree
        if re.search(r"for\s*\(\s*\w[\w<>,\s\[\]]*\s+(\w+)\s*:\s*(\w+)\s*\)", body):
            m = re.search(r"for\s*\(\s*\w[\w<>,\s\[\]]*\s+(\w+)\s*:\s*(\w+)\s*\)", body)
            coll = m.group(2)
            if re.search(r"\b%s\.(?:add|remove|clear|put)\s*\(" % re.escape(coll), body):
                findings.append(Finding(
                    rule="BUG.CONCURRENT_MODIFICATION", category=CAT_BUG, severity=CRITICAL,
                    message="Collection modifiee pendant son parcours : ConcurrentModificationException a l'execution.",
                    fix="Parcourir une copie, utiliser un Iterator avec remove(), ou removeIf().",
                    file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                    evidence=sf.snippet(fn.start),
                ))
        # division entiere ou division par une variable sans garde
        if re.search(r"(?<![/*])/\s*(?:size\(\)|length|count|total|n)\b", body) and \
                not re.search(r"(?:==\s*0|!=\s*0|>\s*0|isEmpty|> 0)", body):
            findings.append(Finding(
                rule="BUG.DIV_ZERO", category=CAT_BUG, severity=MAJOR,
                message="Division par une valeur qui peut valoir zero, sans garde.",
                fix="Verifier que le diviseur est non nul avant la division, et decider du resultat attendu dans ce cas.",
                file=sf.path, line=fn.start, end_line=fn.end, symbol=fn.qualified,
                evidence=sf.snippet(fn.start),
            ))
    return findings
