# Découvrir le contexte du projet

À faire **à chaque invocation**, avant toute conclusion. Rien n'est supposé d'un projet à l'autre : ni chemin, ni module, ni technologie, ni décision. Ce qui a été vu dans un autre dépôt, ou plus tôt dans une autre conversation, ne vaut pas ici.

## Ce qu'il faut établir

| Élément | Où regarder | Si absent |
|---|---|---|
| Racine et périmètre | `git rev-parse --show-toplevel`, dossier courant, plusieurs dépôts ? | travailler sur le dossier courant et le dire |
| Instructions locales | `CLAUDE.md`, `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/rules/`, `CONTRIBUTING.md` | aucune convention locale : appliquer la politique générale |
| État Git | `git status --short --branch`, branche de base | pas de dépôt Git : pas de sélection par diff possible |
| Technologies et build | `pom.xml`, `build.gradle*`, `package.json`, `pyproject.toml`, `go.mod`, `*.csproj`, `Cargo.toml`… | le noter ; ne pas deviner |
| **Tous** les modules | modules Maven/Gradle, workspaces, sous-projets, dossiers de service — pas seulement celui ouvert dans l'IDE | lister ce qui a été vu et ce qui ne l'a pas été |
| Registre(s) d'ADR | `.archgate/adrs/`, dossiers `adr`, `adrs`, `decisions`, `architecture-decisions` à toute profondeur, fichiers `ADR-*.md`, mentions dans la documentation | « aucun registre d'ADR » est un résultat, pas un échec |
| Dossier arc42 | dossier ou fichiers `arc42`, sections numérotées 1 à 12, section 9 | pas d'index des décisions : le signaler |
| OpenSpec | `openspec/config.yaml`, `openspec/changes/`, `openspec/specs/` ; `openspec --version`, `openspec list --json` | voir plus bas |
| Archgate | `.archgate/config.json`, `.archgate/adrs/*.rules.ts` ; `archgate --version`, `archgate adr list` | voir plus bas |
| Tests d'architecture | classes ArchUnit (`com.tngtech.archunit`), dependency-cruiser, import-linter, modules Spring Modulith… | « aucun contrôle automatisé » |
| Commandes de validation | celles que documentent les instructions locales, le README ou la CI (`.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`) | ne pas en inventer |

Le script `adr_tool.py inventory --root <racine>` fait l'inventaire des ADR et du dossier arc42 quand Python est disponible. Sinon : recherche par motifs de fichiers et lecture. Dans les deux cas, lire les documents ; le script ne voit que des formes.

## Quand un composant manque

Le signaler en une ligne dans la restitution et adapter le travail. **Ne rien installer, ne rien initialiser** : pas de `archgate init`, pas de `openspec init`, pas de création d'un dossier `adr/` ou `arc42/`, pas d'installation de paquet — sauf demande explicite de l'utilisateur dans la conversation.

| Manque | Ce que le skill fait quand même |
|---|---|
| Aucun ADR | audit : décisions structurantes observées, présentées comme **propositions à confirmer** ; rédaction : brouillon dans la conversation, emplacement proposé |
| Pas d'arc42 | pas de contrôle d'index ni de vues ; le dire |
| Pas d'OpenSpec | la revue d'impact se fait sur la demande ou le diff |
| CLI `archgate` absent, `.archgate/` présent | lire les ADR et les règles comme des fichiers ; **aucune règle n'a été exécutée** |
| `.archgate/` absent, CLI présent | il n'y a aucune règle Archgate à exécuter ; ce n'est pas une conformité |
| Pas de tests d'architecture | la contrainte relève de la revue humaine |
| Build impossible (outil, réseau, secret) | consigner la commande, l'erreur, et « non exécuté » |

## Priorité des sources

1. Demande de l'utilisateur dans la conversation.
2. Instructions du projet (`CLAUDE.md`, `AGENTS.md`, règles locales).
3. Politique générale (`policy.md`) et gabarits de ce dossier.

Si le projet impose un format d'ADR, un vocabulaire de statuts ou un emplacement, c'est lui qu'on suit ; les gabarits d'ici ne sont qu'un repli.

## Outils du projet

- Le CLI fait foi sur lui-même : `archgate <commande> --help`, `openspec instructions <artefact> --change <nom> --json`. Les formats cités dans ces ressources ont été observés sur des versions précises ; une autre version peut différer.
- Vérifier la liste des skills disponibles avant de supposer une commande `/opsx:*` ou un autre skill.
- Un MCP d'IDE (JetBrains…) aide à naviguer s'il est disponible et ouvert sur le bon projet ; il n'est jamais requis.
