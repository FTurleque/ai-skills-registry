"""Lecture du code source : langages, nettoyage, extraction des fonctions, diff git.

Appels a git : `run_git` lance `git` avec une liste d'arguments, sans shell, et chaque appelant place
les chemins apres `--` : un nom de fichier du depot supervise ne peut ni ajouter une commande ni etre
pris pour une option. Le constat « commande construite a partir de valeurs dynamiques » du superviseur
sur `run_git` est un faux positif."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

C_FAMILY = {
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".scala": "scala",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".tsx": "ts",
    ".cs": "csharp", ".go": "go", ".rs": "rust", ".swift": "swift",
    ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".php": "php", ".groovy": "groovy", ".dart": "dart",
}
INDENT_FAMILY = {".py": "python", ".pyi": "python"}
OTHER_CODE = {
    ".sql": "sql", ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
    ".rb": "ruby", ".yml": "yaml", ".yaml": "yaml", ".xml": "xml",
    ".json": "json", ".tf": "terraform", ".gradle": "groovy",
}

ALL_LANGS = {}
ALL_LANGS.update(C_FAMILY)
ALL_LANGS.update(INDENT_FAMILY)
ALL_LANGS.update(OTHER_CODE)

# Fichiers dont la structure est analysee (fonctions, complexite, duplication).
STRUCTURAL = set(C_FAMILY) | set(INDENT_FAMILY)

TEST_HINTS = (
    "/test/", "/tests/", "\\test\\", "\\tests\\", "/src/test/", "/it/",
    "__tests__", "/spec/", "/testfixtures/", "/fixtures/",
)
TEST_NAME_HINTS = ("test", "spec", "_test", "test_", "it")


def lang_of(path: str) -> Optional[str]:
    return ALL_LANGS.get(os.path.splitext(path)[1].lower())


def is_structural(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in STRUCTURAL


def is_c_family(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in C_FAMILY


def is_python(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in INDENT_FAMILY


def is_test_file(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    if any(h in p for h in (h.replace("\\", "/") for h in TEST_HINTS)):
        return True
    base = os.path.basename(p)
    stem = os.path.splitext(base)[0]
    return stem.startswith("test") or stem.endswith(("test", "tests", "spec", "_spec", "it"))


@dataclass
class SourceFile:
    path: str                       # relatif au depot, separateurs /
    abspath: str
    lang: str
    text: str
    lines: List[str] = field(default_factory=list)      # lignes brutes
    clean_lines: List[str] = field(default_factory=list)  # commentaires et litteraux neutralises
    changed: Set[int] = field(default_factory=set)      # lignes modifiees (1-indexe), vide = tout le fichier
    is_new: bool = False
    is_test: bool = False

    @property
    def nb_lines(self) -> int:
        return len(self.lines)

    def is_changed(self, line: int, slack: int = 2) -> bool:
        if not self.changed:
            return True
        for d in range(-slack, slack + 1):
            if (line + d) in self.changed:
                return True
        return False

    def range_changed(self, start: int, end: int) -> bool:
        if not self.changed:
            return True
        return any(start <= l <= end for l in self.changed)

    def snippet(self, line: int, width: int = 160) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1].strip()[:width]
        return ""


def _scrub_c_like(text: str) -> str:
    """Remplace commentaires et litteraux par des blancs / placeholders, en gardant
    la geometrie du fichier (meme nombre de lignes, meme longueur de ligne)."""
    out = []
    i, n = 0, len(text)
    state = None  # None | "line" | "block" | "str" | "char" | "tpl"
    quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; out.append("  "); i += 2; continue
            if c == "#" and (i == 0 or text[i - 1] == "\n"):
                # directive preprocesseur ou shebang : garde la ligne
                out.append(c); i += 1; continue
            if c == '"':
                if text[i:i + 3] == '"""':
                    state = "str"; quote = '"""'; out.append('"""'); i += 3; continue
                state = "str"; quote = '"'; out.append('"'); i += 1; continue
            if c == "'":
                state = "char"; quote = "'"; out.append("'"); i += 1; continue
            if c == "`":
                state = "tpl"; quote = "`"; out.append("`"); i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                state = None; out.append("\n")
            else:
                out.append(" ")
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = None; out.append("  "); i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        # dans un litteral
        if c == "\\" and state in ("str", "char", "tpl"):
            out.append("  "); i += 2; continue
        if state == "str" and quote == '"""' and text[i:i + 3] == '"""':
            state = None; out.append('"""'); i += 3; continue
        if c == quote and not (state == "str" and quote == '"""'):
            state = None; out.append(c); i += 1; continue
        out.append("\n" if c == "\n" else "_"); i += 1; continue
    return "".join(out)


def _scrub_python(text: str) -> str:
    out = []
    i, n = 0, len(text)
    state = None
    quote = ""
    while i < n:
        c = text[i]
        if state is None:
            if c == "#":
                state = "line"; out.append(" "); i += 1; continue
            if c in "\"'":
                tri = text[i:i + 3]
                if tri in ('"""', "'''"):
                    state = "str"; quote = tri; out.append(tri); i += 3; continue
                state = "str"; quote = c; out.append(c); i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                state = None; out.append("\n")
            else:
                out.append(" ")
            i += 1; continue
        if c == "\\":
            out.append("  "); i += 2; continue
        if len(quote) == 3 and text[i:i + 3] == quote:
            state = None; out.append(quote); i += 3; continue
        if len(quote) == 1 and c == quote:
            state = None; out.append(c); i += 1; continue
        out.append("\n" if c == "\n" else "_"); i += 1; continue
    return "".join(out)


def scrub(text: str, path: str) -> str:
    if is_python(path):
        return _scrub_python(text)
    return _scrub_c_like(text)


# --------------------------------------------------------------------------- git

def run_git(args: List[str], cwd: str, timeout: int = 20) -> Tuple[int, str]:
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except Exception:
        return 1, ""


def git_root(cwd: str) -> Optional[str]:
    rc, out = run_git(["rev-parse", "--show-toplevel"], cwd)
    if rc == 0 and out.strip():
        return out.strip()
    return None


def git_changed_files(root: str) -> Tuple[Set[str], Set[str]]:
    """Retourne (fichiers modifies, fichiers nouveaux) relatifs a la racine."""
    changed, new = set(), set()
    rc, out = run_git(["status", "--porcelain", "-z", "--untracked-files=all"], root)
    if rc != 0:
        return changed, new
    for entry in out.split("\0"):
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if " -> " in path:          # renomme
            path = path.split(" -> ")[-1]
        path = path.strip().strip('"')
        if not path:
            continue
        if code.strip() in ("??", "A", "AM", "A "):
            new.add(path)
        changed.add(path)
    return changed, new


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def git_changed_lines(root: str, paths: List[str]) -> Dict[str, Set[int]]:
    """Lignes ajoutees/modifiees par fichier, via git diff -U0 (index + worktree)."""
    result: Dict[str, Set[int]] = {}
    if not paths:
        return result
    for extra in (["diff", "-U0", "--no-color", "--"], ["diff", "-U0", "--no-color", "--cached", "--"]):
        rc, out = run_git(extra + paths, root, timeout=30)
        if rc != 0:
            continue
        current = None
        for line in out.splitlines():
            if line.startswith("+++ b/"):
                current = line[6:].strip()
                result.setdefault(current, set())
                continue
            m = _HUNK.match(line)
            if m and current:
                start = int(m.group(1))
                count = int(m.group(2) or 1)
                for i in range(start, start + max(count, 1)):
                    result[current].add(i)
    return result


def git_diff_text(root: str, paths: List[str], max_chars: int) -> str:
    """Diff unifie compact, tronque, pour le brief envoye au LLM."""
    chunks = []
    total = 0
    rc, out = run_git(["diff", "-U3", "--no-color", "--"] + paths, root, timeout=30)
    if out:
        chunks.append(out)
        total += len(out)
    rc, out = run_git(["diff", "-U3", "--no-color", "--cached", "--"] + paths, root, timeout=30)
    if out:
        chunks.append(out)
        total += len(out)
    text = "\n".join(chunks)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... diff tronque ...]\n"
    return text


# --------------------------------------------------------------------------- chargement

def _read_text(abspath: str, max_bytes: int):
    """Contenu texte d'un fichier, ou None s'il est trop gros, binaire ou illisible."""
    try:
        if os.path.getsize(abspath) > max_bytes:
            return None
        with open(abspath, "rb") as fh:
            raw = fh.read()
    except OSError as err:
        # Fichier supprime entre-temps ou inaccessible : il n'est pas relu, mais on le dit.
        sys.stderr.write("superviseur : %s illisible, ignore (%s)\n" % (abspath, err))
        return None
    if b"\0" in raw[:4096]:
        return None
    return raw.decode("utf-8", "replace")


def load(root: str, rel_paths, changed_lines=None, new_files=None, max_bytes=600000) -> List[SourceFile]:
    changed_lines = changed_lines or {}
    new_files = new_files or set()
    files = []
    for rel in rel_paths:
        rel_norm = rel.replace("\\", "/")
        abspath = os.path.join(root, rel_norm)
        if not os.path.isfile(abspath):
            continue
        text = _read_text(abspath, max_bytes)
        if text is None:
            continue
        lang = lang_of(rel_norm)
        if not lang:
            continue
        sf = SourceFile(
            path=rel_norm, abspath=abspath, lang=lang, text=text,
            lines=text.splitlines(),
            clean_lines=scrub(text, rel_norm).splitlines(),
            changed=set(changed_lines.get(rel_norm, set())),
            is_new=rel_norm in new_files,
            is_test=is_test_file(rel_norm),
        )
        if sf.is_new:
            sf.changed = set()      # tout le fichier est neuf
        files.append(sf)
    return files


# --------------------------------------------------------------------------- fonctions

@dataclass
class Function:
    name: str
    start: int          # ligne de la signature, 1-indexe
    end: int            # derniere ligne du corps
    params: List[str]
    body: List[str]     # lignes nettoyees du corps
    owner: str = ""     # classe englobante si connue
    returns: str = ""   # type de retour declare, best effort
    modifiers: str = ""

    @property
    def length(self) -> int:
        return max(0, self.end - self.start)

    @property
    def qualified(self) -> str:
        return ("%s.%s" % (self.owner, self.name)) if self.owner else self.name


_C_SIG = re.compile(
    r"""^[ \t]*
    (?P<mods>(?:(?:public|private|protected|internal|static|final|abstract|synchronized|native|
      default|override|open|suspend|async|export|fun|func|def|sealed|inline|operator|virtual|
      unsafe|extern|const|readonly)\s+)*)
    (?P<ret>[A-Za-z_$][\w$<>\[\],.\s?*&:]*?\s+)?
    (?P<name>[A-Za-z_$][\w$]*)
    \s*\(
    """,
    re.VERBOSE,
)
_C_KEYWORDS_NOT_FUNC = {
    "if", "for", "while", "switch", "catch", "return", "new", "else", "do", "try",
    "synchronized", "case", "throw", "super", "this", "assert", "import", "package",
    "yield", "await", "typeof", "instanceof", "in", "of", "and", "or", "not", "with",
    "elif", "except", "finally", "lambda", "match", "when", "require", "println",
}
_CLASS_DECL = re.compile(
    r"^[ \t]*(?:[\w@\[\]()., ]*\s)?(?:class|interface|enum|record|struct|trait|object)\s+([A-Za-z_$][\w$]*)"
)


def _match_params(sig_text: str) -> Optional[Tuple[List[str], int]]:
    """A partir d'un texte commencant juste apres '(' : retourne (params, index apres ')')."""
    depth = 1
    buf = []
    i = 0
    while i < len(sig_text):
        c = sig_text[i]
        if c in "(<[":
            depth += 1
        elif c in ")>]":
            depth -= 1
            if depth == 0:
                raw = "".join(buf)
                params = [p.strip() for p in _split_top(raw) if p.strip()]
                return params, i + 1
        buf.append(c)
        i += 1
    return None


def _split_top(raw: str) -> List[str]:
    parts, depth, cur = [], 0, []
    for c in raw:
        if c in "(<[{":
            depth += 1
        elif c in ")>]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur)); cur = []
            continue
        cur.append(c)
    parts.append("".join(cur))
    return parts


def extract_functions(sf: SourceFile) -> List[Function]:
    if is_python(sf.path):
        return _extract_python(sf)
    if is_c_family(sf.path):
        return _extract_c(sf)
    return []


_BODY_SEARCH_WINDOW = 400   # caracteres examines apres la liste de parametres pour trouver `{`, `;` ou `=>`


def _line_offsets(lines: List[str]) -> List[int]:
    """Position, dans le texte joint par des sauts de ligne, du premier caractere de chaque ligne."""
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    return offsets


def _function_from_signature(clean: List[str], text: str, offsets: List[int], i: int, match, owner: str) -> Optional[Function]:
    """Fonction dont la signature (reconnue par `match`) commence a la ligne i, ou None : declaration sans corps."""
    after = text[offsets[i] + match.end():]
    parsed = _match_params(after)
    if parsed is None:
        return None
    params, consumed = parsed
    tail = after[consumed:consumed + _BODY_SEARCH_WINDOW]
    # corps = accolade ouvrante avant tout ';'
    brace, semi, arrow = tail.find("{"), tail.find(";"), tail.find("=>")
    returns = (match.group("ret") or "").strip()
    modifiers = (match.group("mods") or "").strip()
    if brace != -1 and (semi == -1 or brace < semi):
        end_abs = _match_brace(text, offsets[i] + match.end() + consumed + brace)
        start_line = i + 1
        end_line = _line_of(offsets, end_abs) if end_abs else min(len(clean), i + 1)
        return Function(
            name=match.group("name"), start=start_line, end=end_line, params=params,
            body=clean[start_line:end_line], owner=owner, returns=returns, modifiers=modifiers,
        )
    if arrow != -1 and (semi == -1 or arrow < semi):
        return Function(
            name=match.group("name"), start=i + 1, end=i + 1, params=params,
            body=[clean[i]], owner=owner, returns=returns, modifiers=modifiers,
        )
    return None


def _function_on_line(clean: List[str], text: str, offsets: List[int], i: int, owner: str) -> Optional[Function]:
    match = _C_SIG.match(clean[i])
    if not match or match.group("name") in _C_KEYWORDS_NOT_FUNC:
        return None
    return _function_from_signature(clean, text, offsets, i, match, owner)


def _extract_c(sf: SourceFile) -> List[Function]:
    clean = sf.clean_lines
    text = "\n".join(clean)
    offsets = _line_offsets(clean)
    functions: List[Function] = []
    classes: List[Tuple[str, int]] = []   # (nom, profondeur d'accolade)
    depth = 0
    for i, line in enumerate(clean):
        class_match = _CLASS_DECL.match(line)
        if class_match:
            classes.append((class_match.group(1), depth))
        else:
            function = _function_on_line(clean, text, offsets, i, classes[-1][0] if classes else "")
            if function:
                functions.append(function)   # on ne saute pas : les fonctions imbriquees restent detectables
        depth += line.count("{") - line.count("}")
        while classes and depth <= classes[-1][1]:
            classes.pop()
    return functions


def _match_brace(text: str, open_idx: int) -> Optional[int]:
    depth = 0
    for i in range(open_idx, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _line_of(offsets: List[int], abs_idx: int) -> int:
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= abs_idx:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


_PY_DEF = re.compile(r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)\s*\(")
_PY_CLASS = re.compile(r"^(?P<indent>[ \t]*)class\s+(?P<name>[A-Za-z_]\w*)")


def _extract_python(sf: SourceFile) -> List[Function]:
    clean = sf.clean_lines
    functions: List[Function] = []
    classes: List[Tuple[int, str]] = []
    for i, line in enumerate(clean):
        cm = _PY_CLASS.match(line)
        if cm:
            indent = len(cm.group("indent").expandtabs(4))
            classes = [c for c in classes if c[0] < indent]
            classes.append((indent, cm.group("name")))
        m = _PY_DEF.match(line)
        if not m:
            continue
        indent = len(m.group("indent").expandtabs(4))
        rest = "\n".join(clean[i:])
        parsed = _match_params(rest[rest.find("(") + 1:])
        params = parsed[0] if parsed else []
        params = [p for p in params if p.split(":")[0].strip() not in ("self", "cls")]
        end = i + 1
        for j in range(i + 1, len(clean)):
            stripped = clean[j].strip()
            if not stripped:
                continue
            j_indent = len(clean[j]) - len(clean[j].lstrip())
            j_indent = len(clean[j][:j_indent].expandtabs(4))
            if j_indent <= indent:
                break
            end = j + 1
        owner = ""
        for ci, cname in classes:
            if ci < indent:
                owner = cname
        return_type = ""
        sig_line = line
        if "->" in sig_line:
            return_type = sig_line.split("->")[-1].split(":")[0].strip()
        functions.append(Function(
            name=m.group("name"), start=i + 1, end=end, params=params,
            body=clean[i + 1:end], owner=owner, returns=return_type, modifiers="",
        ))
    return functions
