"""Caracterisation des regles sur un corpus statique.

Deux familles d'entrees dans `golden/rules.json` :

- `<config>|<selection>|<fichier>` : `check_lines`, `check_blocks` et `check_file`, avec deux jeux de
  seuils (defauts et seuils bas) et deux selections de lignes modifiees (toutes, une sur sept) ;
- `extra|<config>|<fichier>` et `duplication|<config>|<scenario>` : regles de securite, de nommage, d'imports, de
  complexite par fonction, de bugs par fonction, extraction des fonctions et duplication, avec les
  defauts et des seuils de fonction tres bas ;
- `partial|seuils_fonctions|<fichier>` : les memes regles (hors extraction et duplication) quand seule une
  ligne sur sept est modifiee.

Le test echoue aussi si le corpus ne declenche pas toutes les regles que le moteur declare."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile

RULE_MODULES = ("rules_bugs", "rules_quality", "rules_security", "rules_naming", "rules_duplication")
RULE_ID = re.compile(r'"((?:BUG|CNV|CPX|SEC|NAM|DUP)\.[A-Z_]+)"')
# Regles volontairement absentes du corpus, avec la raison. Toute autre regle declaree doit se declencher.
UNCOVERED_RULES = frozenset()
GENERATED_DIR = "generated"


def generated_files() -> dict:
    """Fichiers dont le contenu ressemble a des secrets, assembles a l'execution.

    Le validateur du depot et la protection des secrets de GitHub refusent ces motifs ecrits en clair :
    chaque valeur est donc composee de fragments, et la reference n'en garde qu'une empreinte."""
    aws = "AK" + "IA" + "7Q4ZLM2XN9R3T5VB"
    pem_header = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
    jwt = ".".join(["eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0", "c2lnbmF0dXJlMTIzNDU2"])
    slack = "xox" + "b-123456789012-abcdefghij"
    github = "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
    # Valeur de la documentation d'AWS : le mot « EXAMPLE » la rend factice, la regle doit l'ignorer.
    aws_documentation = "AK" + "IA" + "IOSFODNN7" + "EXAMPLE"
    assignments = [
        'AWS_ACCESS = "%s"' % aws,
        'KEY_HEADER = """%s"""' % pem_header,
        'SESSION_JWT = "%s"' % jwt,
        'SLACK = "%s"' % slack,
        'GITHUB = "%s"' % github,
    ]
    docstring = '"""Corpus de caracterisation : secrets assembles a l\'execution (voir rules_corpus.generated_files)."""'
    return {
        GENERATED_DIR + "/secrets.py": "\n".join([docstring] + assignments + ['AWS_DOCUMENTATION = "%s"' % aws_documentation]) + "\n",
        # En chemin de test, les secrets a format connu restent critiques (les autres sont abaisses).
        GENERATED_DIR + "/tests/test_secrets.py": "\n".join([docstring] + assignments) + "\n",
    }


def _walk(folder: str):
    rels = []
    for base, _, names in os.walk(folder):
        for name in names:
            rels.append(os.path.relpath(os.path.join(base, name), folder).replace("\\", "/"))
    return sorted(rels)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _compact(finding):
    """Un constat sous forme de liste ; le correctif, long et verbeux, est reduit a une empreinte :
    un changement de texte est detecte, sans noyer le diff de la reference. L'extrait des fichiers
    generes l'est aussi, car il contient les valeurs ressemblant a des secrets."""
    evidence = _digest(finding.evidence) if finding.file.startswith(GENERATED_DIR + "/") else finding.evidence
    return [finding.rule, finding.severity, finding.category, finding.line, getattr(finding, "end_line", None),
            finding.message, _digest(finding.fix), evidence, finding.symbol]


def _function_summary(fn):
    """Tout ce que l'extraction produit pour une fonction : le corps n'est conserve que par son empreinte."""
    return [fn.qualified, fn.start, fn.end, list(fn.params), fn.owner, fn.returns, fn.modifiers, fn.length,
            _digest("\n".join(fn.body))]


def _configs(Config, DEFAULTS) -> dict:
    def variant(**thresholds):
        settings = json.loads(json.dumps(DEFAULTS))
        settings["thresholds"].update(thresholds)
        return Config(settings)
    return {
        "defaut": variant(),
        "seuils_bas": variant(line_length=60, file_lines=100),
        # Seuils de fonction tres bas : declenche complexite, imbrication, parametres, taille, condition composee.
        "seuils_fonctions": variant(complexity_warn=2, complexity_critical=4, function_lines_warn=5,
                                    function_lines_critical=10, nesting=2, params=2, boolean_operators=1,
                                    duplication_lines=3),
        # Fenetre courte et un seul constat autorise : exerce le plafond de rapports de duplication.
        "doublons_bas": variant(duplication_lines=3, duplication_max_reports=1),
        # Un seul fichier de reference lu : `os.walk` rend les fichiers d'un dossier avant ceux de ses
        # sous-dossiers, ce qui rend le resultat identique d'un systeme a l'autre.
        "reference_limitee": variant(duplication_corpus_files=1),
    }


def _line_block_file_groups(modules, files_for, configs, result):
    rules_bugs, rules_quality = modules["rules_bugs"], modules["rules_quality"]
    for config_name in ("defaut", "seuils_bas"):
        for selection in ("tout", "un_sur_sept"):
            for sf in files_for(selection):
                result["%s|%s|%s" % (config_name, selection, sf.path)] = {
                    "lines": [_compact(f) for f in rules_bugs.check_lines(sf)],
                    "blocks": [_compact(f) for f in rules_bugs.check_blocks(sf)],
                    "file": [_compact(f) for f in rules_quality.check_file(sf, configs[config_name])],
                }


def _extra_groups(modules, files, configs, result):
    for config_name in ("defaut", "seuils_fonctions"):
        cfg = configs[config_name]
        for sf in files:
            functions = modules["source"].extract_functions(sf) if modules["source"].is_structural(sf.path) else []
            result["extra|%s|%s" % (config_name, sf.path)] = {
                "security": [_compact(f) for f in modules["rules_security"].check(sf)],
                "naming": [_compact(f) for f in modules["rules_naming"].check_identifiers(sf, functions)],
                "imports": [_compact(f) for f in modules["rules_quality"].check_unused_imports(sf)],
                "functions": [_function_summary(fn) for fn in functions],
                "function_quality": [_compact(f) for f in modules["rules_quality"].check_functions(sf, functions, cfg)],
                "function_bugs": [_compact(f) for f in modules["rules_bugs"].check_function_bugs(sf, functions)],
            }


def _partial_groups(modules, files, configs, result):
    """Memes regles, mais seules une ligne sur sept est modifiee : exerce les filtres « ligne modifiee » et
    « plage de fonction modifiee », que la selection complete ne touche jamais."""
    cfg = configs["seuils_fonctions"]
    for sf in files:
        functions = modules["source"].extract_functions(sf) if modules["source"].is_structural(sf.path) else []
        result["partial|seuils_fonctions|%s" % sf.path] = {
            "security": [_compact(f) for f in modules["rules_security"].check(sf)],
            "naming": [_compact(f) for f in modules["rules_naming"].check_identifiers(sf, functions)],
            "imports": [_compact(f) for f in modules["rules_quality"].check_unused_imports(sf)],
            "function_quality": [_compact(f) for f in modules["rules_quality"].check_functions(sf, functions, cfg)],
            "function_bugs": [_compact(f) for f in modules["rules_bugs"].check_function_bugs(sf, functions)],
        }


# Fichiers « modifies » de chaque scenario de duplication (None : tous). La duplication compare ces fichiers
# entre eux puis au reste du dossier, d'ou la variete des scenarios : un seul jeu de fichiers modifies
# n'exercerait jamais la recherche dans le reste du depot.
DUPLICATION_SCENARIOS = {
    "tout": None,
    "java_a": ["java/DuplicateA.java"],
    "java_a_b": ["java/DuplicateA.java", "java/DuplicateB.java"],
    "meme_fichier": ["java/DuplicateSelf.java"],
    "dossier_exclu": ["java/UniqueDir.java"],          # son doublon n'existe que dans un dossier exclu
    "dossier_inclus": ["java/UniquePlain.java"],       # son doublon existe dans un fichier ordinaire
    "motif_exclu": ["js/dup/Unique.js"],               # son doublon n'existe que dans un *.min.js
    "plusieurs_racines": ["java/DuplicateA.java", "js/dup/Unique.js"],
    "fichier_a_la_racine": ["top_level.py"],           # pas de dossier de premier niveau a parcourir
    "test_uniquement": ["java/src/test/java/demo/ServiceTest.java"],
    "hors_structure": ["misc/conf.yaml"],
    "yaml_duplique": ["misc/duplicated.yaml"],          # un bloc repete, mais le YAML n'est pas structurel
    "extension_differente": ["js/dup/CrossTarget.ts"],  # son doublon est un .js : autre extension, pas compare
    "autre_racine": ["java/CrossRoot.java"],            # son doublon est dans un autre dossier de premier niveau
    "limite_de_fichiers": ["limitdup/Target.java"],     # son doublon est dans un sous-dossier, apres un fichier ordinaire
    # La limite est atteinte dans la premiere racine : la seconde, qui seule contient le doublon, n'est pas lue.
    "limite_entre_racines": ["a_first/Anchor.java", "z_second/Target.java"],
}


def _duplication_groups(rules_duplication, everything, corpus, configs, result):
    by_path = {sf.path: sf for sf in everything}
    for config_name in ("defaut", "seuils_fonctions", "doublons_bas", "reference_limitee"):
        for scenario, selected in DUPLICATION_SCENARIOS.items():
            changed = everything if selected is None else [by_path[rel] for rel in selected]
            found = rules_duplication.check(changed, corpus, configs[config_name])
            result["duplication|%s|%s" % (config_name, scenario)] = sorted((_compact(f) for f in found), key=repr)


def run(engine_dir: str, corpus: str) -> dict:
    """Constats de toutes les regles du corpus (voir l'en-tete du module)."""
    sys.path.insert(0, engine_dir)
    try:
        import rules_bugs
        import rules_duplication
        import rules_naming
        import rules_quality
        import rules_security
        import source
        from config import DEFAULTS, Config
    finally:
        sys.path.remove(engine_dir)
    modules = {"rules_bugs": rules_bugs, "rules_duplication": rules_duplication, "rules_naming": rules_naming,
               "rules_quality": rules_quality, "rules_security": rules_security, "source": source}
    configs = _configs(Config, DEFAULTS)
    rels = _walk(corpus)
    result = {}
    with tempfile.TemporaryDirectory() as generated_root:
        generated = generated_files()
        for rel, text in generated.items():
            path = os.path.join(generated_root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)

        def files_for(selection):
            everything = source.load(corpus, rels) + source.load(generated_root, sorted(generated))
            if selection == "tout":
                return everything
            # Une ligne sur sept : `is_changed` accepte une marge de 2 lignes, donc une ligne sur trois les
            # laisserait toutes passer et le filtre ne serait jamais exerce.
            sparse = {sf.path: set(range(1, sf.nb_lines + 1, 7)) for sf in everything}
            return source.load(corpus, rels, changed_lines=sparse) + source.load(
                generated_root, sorted(generated), changed_lines=sparse)

        _line_block_file_groups(modules, files_for, configs, result)
        everything = files_for("tout")
        _extra_groups(modules, everything, configs, result)
        _partial_groups(modules, files_for("un_sur_sept"), configs, result)
        _duplication_groups(rules_duplication, source.load(corpus, rels), corpus, configs, result)
    return result


def declared_rules(engine_dir: str) -> set:
    """Identifiants de regles ecrits dans les modules de regles du moteur."""
    declared = set()
    for module in RULE_MODULES:
        with open(os.path.join(engine_dir, module + ".py"), encoding="utf-8") as fh:
            declared |= set(RULE_ID.findall(fh.read()))
    return declared


def _findings(value):
    """Constats d'une entree, quelle que soit sa forme (liste de constats, ou dictionnaire de listes)."""
    if isinstance(value, dict):
        for part in value.values():
            yield from _findings(part)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, list) and item and isinstance(item[0], str) and re.match(r"[A-Z]{3}\.", item[0]):
                yield item
            else:
                yield from _findings(item)


def check_coverage(result: dict, engine_dir: str) -> list:
    """Regles declarees par le moteur que le corpus ne declenche pas."""
    seen = {finding[0] for entry in result.values() for finding in _findings(entry)}
    return sorted(declared_rules(engine_dir) - UNCOVERED_RULES - seen)
