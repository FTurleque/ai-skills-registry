#!/usr/bin/env python3
"""Tests de caracterisation du superviseur de code.

  python tests/run_tests.py                  compare le moteur aux references de golden/
  python tests/run_tests.py --update         regenere les references (apres un changement voulu)
  python tests/run_tests.py --only rules     une seule suite : `hook` ou `rules`
  python tests/run_tests.py --script ~/.claude/hooks/supervisor.py    teste un moteur installe

Deux suites : les scenarios de bout en bout du hook, et toutes les regles de detection
sur un corpus statique. Elles servent de filet de securite aux refactorisations : une sortie qui
change sans qu'on l'ait voulu fait echouer le test."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hook_scenarios
import rules_corpus

DEFAULT_SCRIPT = os.path.join(os.path.dirname(HERE), "resources", "supervisor.py")
GOLDEN_DIR = os.path.join(HERE, "golden")
CORPUS_DIR = os.path.join(HERE, "corpus")
MAX_DIFFERENCES_SHOWN = 5


def _golden_path(name: str) -> str:
    return os.path.join(GOLDEN_DIR, name + ".json")


def _save(name: str, data: dict) -> None:
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    with open(_golden_path(name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def _load(name: str):
    try:
        with open(_golden_path(name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _describe(key: str, expected, actual) -> str:
    if isinstance(expected, dict) and isinstance(actual, dict) and expected.keys() == actual.keys():
        changed = [field for field in expected if expected[field] != actual[field]]
        detail = ", ".join(changed)
        first = changed[0] if changed else ""
        return "%s : champ(s) %s\n      attendu : %.160r\n      obtenu  : %.160r" % (
            key, detail, expected.get(first), actual.get(first))
    return "%s\n      attendu : %.160r\n      obtenu  : %.160r" % (key, expected, actual)


def _compare(name: str, actual: dict) -> bool:
    expected = _load(name)
    if expected is None:
        print("  ECHEC : reference golden/%s.json absente ou illisible (python tests/run_tests.py --update)" % name)
        return False
    # Les references sont du JSON : on compare les memes types que ceux relus du disque.
    actual = json.loads(json.dumps(actual, ensure_ascii=False))
    differing = sorted(k for k in set(expected) | set(actual) if expected.get(k) != actual.get(k))
    if not differing:
        print("  OK : %d entrees identiques a la reference" % len(expected))
        return True
    print("  ECHEC : %d entree(s) different(s) de la reference" % len(differing))
    for key in differing[:MAX_DIFFERENCES_SHOWN]:
        print("    - " + _describe(key, expected.get(key), actual.get(key)))
    if len(differing) > MAX_DIFFERENCES_SHOWN:
        print("    ... et %d autre(s)" % (len(differing) - MAX_DIFFERENCES_SHOWN))
    return False


def _suite_hook(script: str) -> dict:
    return hook_scenarios.run(script)


def _suite_rules(script: str) -> dict:
    engine_dir = os.path.join(os.path.dirname(os.path.abspath(script)), "supervisor")
    result = rules_corpus.run(engine_dir, CORPUS_DIR)
    missing = rules_corpus.check_coverage(result, engine_dir)
    if missing:
        raise SystemExit("ECHEC : le corpus ne declenche plus ces regles : %s" % ", ".join(missing))
    return result


SUITES = {"hook": ("hook_scenarios", _suite_hook), "rules": ("rules", _suite_rules)}


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="Tests de caracterisation du superviseur de code.")
    parser.add_argument("--update", action="store_true", help="regenere les references")
    parser.add_argument("--only", choices=sorted(SUITES), help="une seule suite")
    parser.add_argument("--script", default=DEFAULT_SCRIPT, help="supervisor.py a tester")
    args = parser.parse_args(argv)
    script = os.path.abspath(args.script)
    if not os.path.isfile(script):
        print("supervisor.py introuvable : %s" % script)
        return 2
    failed = False
    for key, (golden_name, suite) in SUITES.items():
        if args.only and args.only != key:
            continue
        print("[%s]" % key)
        actual = suite(script)
        if args.update:
            _save(golden_name, actual)
            print("  reference golden/%s.json ecrite (%d entrees)" % (golden_name, len(actual)))
        elif not _compare(golden_name, actual):
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
