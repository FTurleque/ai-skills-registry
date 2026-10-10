# Politique ADR (ressources partagées)

> La politique, les procédures et les gabarits communs aux skills `adr-audit`, `adr-author` et `adr-check`, en un seul exemplaire.

## Ce que ça change

Les trois skills ADR ont besoin des mêmes textes : le filtre de pertinence, la façon de découvrir un projet, l'articulation avec arc42 et OpenSpec, le comportement réel d'Archgate, les gabarits. Les recopier dans chacun donnerait trois versions qui divergent à la première retouche. Ce dossier les porte une fois ; chaque skill y renvoie par un chemin relatif.

Ce n'est pas un skill qu'on appelle : `user-invocable: false` et `disable-model-invocation: true` le retirent du menu `/` et de la liste que Claude consulte. Il a la forme d'un skill pour s'installer et se versionner comme les trois autres.

## Installation

Il s'installe **avec** les trois skills, dans le même dossier :

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/adr-policy/` | oui (Windows 10, Claude Code 2.1.292) |
| Claude Code, portée projet | `<projet>/.claude/skills/adr-policy/` | non vérifié |

```bash
cp -r skills/architecture/adr-policy skills/architecture/adr-audit skills/architecture/adr-author skills/architecture/adr-check ~/.claude/skills/
```

Sous Windows, `~` est `%USERPROFILE%`. Copier les dossiers **entiers** et **côte à côte** : les trois skills lisent `../adr-policy/resources/`.

Prérequis facultatif : Python 3.8+ pour `resources/adr_tool.py`. Sans lui, les skills font l'inventaire par recherche de fichiers.

## Usage

Rien à invoquer. Pour lire ou adapter la politique : `resources/policy.md`. Le script s'utilise aussi seul :

```bash
python ~/.claude/skills/adr-policy/resources/adr_tool.py inventory --root .
python ~/.claude/skills/adr-policy/resources/adr_tool.py check --root . --json
```

`inventory` liste les ADR trouvés (identifiant, statut déclaré, format, emplacement) et le dossier arc42. `check` signale identifiants en double, registres multiples, titres proches, statuts illisibles, `rules: true` sans fichier de règles, liens cassés, ADR absents de l'index arc42 §9 et statuts divergents. Codes de sortie : `0` rien, `1` constats, `2` erreur d'usage.

## Contenu

| Fichier | Rôle |
|---------|------|
| `resources/policy.md` | filtre de pertinence, cinq conclusions, statuts, validation humaine, historique, étiquettes de preuve |
| `resources/discovery.md` | ce qu'il faut découvrir dans un projet, conduite quand un composant manque |
| `resources/arc42-openspec.md` | index en section 9, sections à revoir, revue d'impact architectural, contrôle avant archivage |
| `resources/archgate.md` | Archgate CLI 0.59.0 : commandes, formats, sélection par diff, initialisation sans plugin |
| `resources/verification.md` | rendre une décision vérifiable, trois catégories de résultat |
| `resources/templates/adr.md` | gabarit d'ADR, deux variantes, procédure de remplacement |
| `resources/templates/reports.md` | restitutions des trois skills |
| `resources/adr_tool.py` | inventaire et contrôles de forme |
| `resources/tests/test_adr_tool.py` | 21 tests (`python -m unittest discover -s resources/tests`) |
| `examples/` | comportement d'Archgate relevé par exécution |

## Limites

- **`resources/archgate.md` décrit Archgate 0.59.0 sous Windows 10**, par exécution. Une autre version peut se comporter autrement, en particulier sur la sélection par diff : `archgate <commande> --help` et un essai font foi.
- **La politique est une convention, pas un mécanisme.** Rien n'empêche techniquement de créer un ADR sans passer le filtre ; les skills l'appliquent parce que leurs instructions le demandent.
- **`adr_tool.py` ne voit que des formes.** Il reconnaît un ADR à son emplacement (`.archgate/adrs/`, dossiers `adr`, `adrs`, `decisions`…) ou à son nom (`ADR-*.md`) : un ADR rangé ailleurs sous un autre nom lui échappe. La détection des doublons compare des titres ; elle propose, elle ne tranche pas. Le front matter est lu par un analyseur réduit (scalaires et listes), pas par une bibliothèque YAML.
- **Statuts reconnus en français et en anglais seulement.**
- **`adr_tool.py` n'a été exécuté qu'avec Python 3.13** ; la compatibilité 3.8+ est visée (bibliothèque standard) mais non vérifiée.
- **Surface `claude-code` seule.** Le renvoi `${CLAUDE_SKILL_DIR}/../adr-policy/` suppose un système de fichiers et des skills installés côte à côte ; sur claude.ai ou via l'API, non vérifié.
