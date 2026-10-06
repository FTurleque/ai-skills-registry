"""Nommage : les identifiants doivent dire ce qu'ils representent."""
from __future__ import annotations

import re
from typing import List

from model import MAJOR, MINOR, CAT_NAMING, Finding
from source import SourceFile, Function, is_python

# Noms qui ne portent aucune information. En francais comme en anglais.
VAGUE = {
    "tmp", "temp", "tmp1", "tmp2", "data", "data1", "data2", "datas", "info", "infos",
    "obj", "object", "objet", "val", "value1", "values1", "var", "var1", "var2",
    "foo", "bar", "baz", "qux", "toto", "titi", "tata", "truc", "machin", "bidule",
    "chose", "stuff", "thing", "things", "misc", "aux", "dummy", "test1", "test2",
    "res", "res1", "retval", "ret", "out1", "output1", "input1", "arr", "arr1",
    "lst", "liste", "list1", "tab", "tableau", "map1", "dict1", "item1", "elem1",
    "flag", "flag1", "bool1", "str1", "s1", "s2", "d1", "d2", "o1", "o2", "x1", "x2",
    "mystring", "myvar", "myobject", "mylist", "mymap", "helper", "util", "utils",
    "manager1", "handler1", "process1", "doit", "dostuff", "dothing", "dowork",
    "calcul", "calcul1", "traitement", "traiter", "faire", "gerer", "truc1",
}
ABBREVIATIONS = {
    "usr": "user", "cust": "customer", "addr": "address", "cnt": "count", "nb": "count",
    "qte": "quantity", "mgr": "manager", "ctrl": "controller", "cfg": "config",
    "ctx": "context", "repo": "repository", "msg": "message", "err": "error",
    "resp": "response", "req": "request", "btn": "button", "evt": "event",
    "attr": "attribute", "prop": "property", "arg": "argument", "param": "parameter",
    "num": "number", "pos": "position", "len": "length", "idx": "index",
    "dt": "date", "ts": "timestamp", "amt": "amount", "pct": "percent",
}
# Ces abbreviations sont tolerees : usage universel.
ABBREV_OK = {"id", "ids", "url", "uri", "uuid", "io", "db", "api", "http", "json", "xml",
             "sql", "ok", "ip", "os", "ui", "dto", "dao", "jwt", "csv", "pdf", "min", "max",
             "i", "j", "k", "n", "e", "ex", "sb", "it", "to", "from", "at", "by", "on", "of",
             "in", "up", "fs", "ms", "ns", "kb", "mb", "gb", "key", "row", "col", "end"}
LOOP_OK = {"i", "j", "k", "n", "x", "y", "z", "e", "ex", "it", "_"}

BOOL_PREFIXES = ("is", "has", "can", "should", "must", "was", "were", "are", "does", "did",
                 "contains", "exists", "equals", "matches", "supports", "allows", "needs",
                 "est", "a_", "peut", "doit")
BOOL_TYPES = {"boolean", "bool", "Boolean"}
# Verbes d'action : un booleen en retour trahit alors un nom qui ne dit pas ce que fait la methode.
ACTION_VERBS = {"get", "compute", "calculate", "calculer", "make", "build", "load", "create",
                "do", "handle", "process", "parse", "read", "write", "update", "set", "fetch",
                "send", "save", "run", "execute", "apply", "resolve", "convert", "transform"}
SIDE_EFFECTS = re.compile(
    r"(?<![\w.])(?:save|persist|insert|update|delete|remove|create|write|send|publish|commit|"
    r"flush|set[A-Z]|put\s*\(|add\s*\(|clear\s*\(|execute|dispatch|notify)")

_IDENT_DECL_C = re.compile(
    r"(?:^|[;{(,]|\breturn\b|\bnew\b|=)\s*(?:final\s+|const\s+|let\s+|var\s+|static\s+)?"
    r"(?:[A-Za-z_$][\w$]*(?:<[^<>;=]{0,60}>)?(?:\[\])?)\s+([a-z_$][\w$]*)\s*(?==[^=]|;|,|\))"
)
_PY_ASSIGN = re.compile(r"^\s*([a-z_]\w*)\s*(?::\s*[\w\[\], .]+)?\s*=(?!=)")


def _split_words(name: str) -> List[str]:
    parts = re.split(r"[_\-]", name)
    words = []
    for p in parts:
        words.extend(re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", p))
    return [w.lower() for w in words if w]


def _is_vague(name: str) -> bool:
    low = name.lower()
    if low in VAGUE:
        return True
    words = _split_words(name)
    if words and all(w in VAGUE or w.isdigit() for w in words):
        return True
    return False


def _too_short(name: str) -> bool:
    low = name.lower()
    if low in ABBREV_OK or low in LOOP_OK:
        return False
    return len(name.strip("_")) <= 2


_NOT_NAMES = ("return", "new", "if", "else", "this", "self")
_GENERIC_VERBS = ("do", "handle", "manage", "process", "traiter", "gerer", "faire")
_LOOP_START = re.compile(r"^\s*(?:for|while)\b")
_ENDS_WITH_DIGIT = re.compile(r"[a-zA-Z]\d$")
_CAMEL_CASE = re.compile(r"^[a-z$_][\w$]*$")
_PASCAL_CASE = re.compile(r"^[A-Z][\w$]*$")
_SNAKE_CASE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
_IDENTIFIER = re.compile(r"^[A-Za-z_$][\w$]*$")
_SKIPPED_LINE_PREFIXES = ("import", "package", "from ", "@")


class _Collector:
    """Constats de nommage d'un fichier, sans doublon : une meme regle ne se repete pas pour un meme nom et un
    meme symbole, qu'il soit rencontre comme variable ou comme fonction."""

    def __init__(self, sf: SourceFile):
        self.sf = sf
        self.findings: List[Finding] = []
        self._seen = set()

    def add(self, rule, sev, name, line, msg, fix, symbol=None):
        key = (rule, name, symbol)
        if key in self._seen:
            return
        self._seen.add(key)
        self.findings.append(Finding(
            rule=rule, category=CAT_NAMING, severity=sev, message=msg, fix=fix,
            file=self.sf.path, line=line, symbol=symbol or name, evidence=self.sf.snippet(line),
        ))


# ----------------------------------------------------------------------- variables locales et champs

def _declared_names(sf: SourceFile, clean: str) -> List[str]:
    if is_python(sf.path):
        match = _PY_ASSIGN.match(clean)
        return [match.group(1)] if match else []
    return list(_IDENT_DECL_C.findall(clean))


def _check_abbreviation(out: _Collector, name: str, idx: int) -> None:
    for word in _split_words(name):
        if word in ABBREVIATIONS and word not in ABBREV_OK:
            out.add("NAM.ABBREVIATION", MINOR, name, idx,
                    "Le nom `%s` utilise l'abreviation `%s`." % (name, word),
                    "Ecrire le mot en entier (`%s`) pour rester coherent et lisible." % ABBREVIATIONS[word])
            return


def _check_numbered(out: _Collector, name: str, idx: int) -> None:
    if _ENDS_WITH_DIGIT.search(name) and name.lower() not in ABBREV_OK:
        out.add("NAM.NUMBERED", MINOR, name, idx,
                "Le nom `%s` se termine par un chiffre : il distingue mal deux concepts." % name,
                "Nommer chaque variable d'apres son role (`montantHT` / `montantTTC` plutot que `montant1` / `montant2`).")


def _check_variable(out: _Collector, name: str, idx: int, in_loop: bool) -> None:
    if name in _NOT_NAMES:
        return
    if _is_vague(name):
        out.add("NAM.VAGUE_VARIABLE", MAJOR, name, idx,
                "La variable `%s` ne dit pas ce qu'elle contient." % name,
                "La renommer d'apres la donnee qu'elle porte (ce qu'elle est, pas son type) : par exemple `clientsActifs` au lieu de `liste`.")
    elif _too_short(name) and not in_loop:
        out.add("NAM.TOO_SHORT", MINOR, name, idx,
                "Le nom `%s` est trop court pour etre compris hors contexte." % name,
                "Donner un nom complet ; les noms d'une lettre ne se justifient que pour un compteur de boucle.")
    else:
        _check_abbreviation(out, name, idx)
        _check_numbered(out, name, idx)


def _check_variables(sf: SourceFile, out: _Collector) -> None:
    for idx, clean in enumerate(sf.clean_lines, start=1):
        if not sf.is_changed(idx):
            continue
        stripped = clean.strip()
        if not stripped or stripped.startswith(_SKIPPED_LINE_PREFIXES):
            continue
        in_loop = bool(_LOOP_START.match(stripped))
        for name in _declared_names(sf, clean):
            _check_variable(out, name, idx, in_loop)


# ----------------------------------------------------------------------- fonctions

def _check_function_name(out: _Collector, fn: Function) -> None:
    name = fn.name
    if _is_vague(name):
        out.add("NAM.VAGUE_METHOD", MAJOR, name, fn.start,
                "La methode `%s` a un nom qui ne decrit pas son effet." % fn.qualified,
                "La renommer avec un verbe precis sur un objet precis (`calculerSoldeDisponible`, `envoyerRelanceClient`).", fn.qualified)
    words = _split_words(name)
    if words and words[0] in _GENERIC_VERBS and len(words) == 1:
        out.add("NAM.VAGUE_VERB", MAJOR, name, fn.start,
                "La methode `%s` utilise un verbe passe-partout." % fn.qualified,
                "Nommer l'action reellement effectuee ; si aucun verbe precis ne convient, la methode fait probablement plusieurs choses et doit etre decoupee.", fn.qualified)


def _check_function_contract(out: _Collector, fn: Function) -> None:
    """Ce que le nom promet (bool, getter) face a ce que la methode retourne et fait."""
    name = fn.name
    return_type = fn.returns.replace("final", "").strip()
    is_bool = return_type in BOOL_TYPES or fn.returns.strip().endswith("bool")
    # Un adjectif ou un participe (reusable, windows, startsWith) se lit deja comme une
    # assertion. Ce qui pose probleme, c'est un verbe d'action qui renvoie un booleen.
    if is_bool and _split_words(name) and _split_words(name)[0] in ACTION_VERBS:
        out.add("NAM.BOOL_PREFIX", MINOR, name, fn.start,
                "La methode `%s` est nommee comme une action mais retourne un booleen." % fn.qualified,
                "Renommer en question (is/has/can/should/contains) si elle ne fait que repondre oui ou non ; sinon faire retourner le resultat de l'action.", fn.qualified)
    if not name.startswith("get"):
        return
    if return_type == "void":
        out.add("NAM.GETTER_VOID", MAJOR, name, fn.start,
                "La methode `%s` commence par get mais ne retourne rien." % fn.qualified,
                "Renommer d'apres l'action reelle (load, refresh, compute) ou faire retourner la valeur attendue.", fn.qualified)
    if SIDE_EFFECTS.search("\n".join(fn.body)) and fn.length > 5:
        out.add("NAM.GETTER_SIDE_EFFECT", MAJOR, name, fn.start,
                "La methode `%s` s'annonce comme un accesseur mais modifie l'etat du systeme." % fn.qualified,
                "Separer la lecture de l'ecriture : un `get*` ne doit pas ecrire ; nommer l'operation d'ecriture explicitement.", fn.qualified)


def _check_function_case(sf: SourceFile, out: _Collector, fn: Function) -> None:
    name = fn.name
    if len(name) > 3 and not is_python(sf.path) and not _CAMEL_CASE.match(name) and not _PASCAL_CASE.match(name):
        out.add("NAM.CASE", MINOR, name, fn.start,
                "Le nom `%s` ne suit pas la convention de casse du langage." % name,
                "Utiliser camelCase pour les methodes et PascalCase pour les types.", fn.qualified)
    if is_python(sf.path) and not _SNAKE_CASE.match(name):
        out.add("NAM.CASE", MINOR, name, fn.start,
                "Le nom `%s` ne suit pas la convention snake_case de Python." % name,
                "Renommer en snake_case.", fn.qualified)


def _parameter_name(declaration: str) -> str:
    return declaration.split("=")[0].split(":")[0].strip().split(" ")[-1].strip("*&")


def _check_parameters(out: _Collector, fn: Function) -> None:
    for declaration in fn.params:
        name = _parameter_name(declaration)
        if _IDENTIFIER.match(name or "") and _is_vague(name):
            out.add("NAM.VAGUE_PARAM", MINOR, name, fn.start,
                    "Le parametre `%s` de `%s` ne dit pas ce qu'il recoit." % (name, fn.qualified),
                    "Nommer le parametre d'apres la donnee attendue.", fn.qualified)


def _check_function(sf: SourceFile, out: _Collector, fn: Function) -> None:
    _check_function_name(out, fn)
    _check_function_contract(out, fn)
    _check_function_case(sf, out, fn)
    _check_parameters(out, fn)


def check_identifiers(sf: SourceFile, functions: List[Function]) -> List[Finding]:
    out = _Collector(sf)
    _check_variables(sf, out)
    for fn in functions:
        if sf.range_changed(fn.start, fn.end):
            _check_function(sf, out, fn)
    return out.findings
