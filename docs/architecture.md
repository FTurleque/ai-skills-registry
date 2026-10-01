# Architecture du dépôt

Ce document décrit l'organisation de **AI Toolkit Registry** : ce que contient chaque dossier, et la
règle qui décide où va un nouvel artefact.

---

## La règle de rangement

> **Le dossier dit le mécanisme, pas le sujet.**

Un outil de revue de code peut être une skill, un sous-agent, un plugin, ou les trois à la fois. Ce
qui décide de son emplacement n'est pas ce dont il parle, mais la façon dont il s'exécute :

| Question | Réponse | Dossier |
|----------|---------|---------|
| Claude lit du texte et change sa façon de travailler ? | skill | `skills/` |
| Du code s'exécute sur un événement, sans être appelé ? | hook | `hooks/` |
| C'est un paquet installable qui branche plusieurs composants ? | plugin | `plugins/` |
| C'est un assistant qui travaille à côté, dans son propre contexte ? | sous-agent | `agents/` |
| C'est un raccourci que l'utilisateur tape ? | commande | `commands/` |
| C'est le contexte qu'un dépôt donne à Claude au démarrage ? | instructions | `instructions/` |
| C'est le branchement d'outils externes ? | serveur MCP | `mcp/` |
| C'est une posture de réponse permanente ? | style de sortie | `output-styles/` |

Un artefact qui semble appartenir à deux dossiers est généralement deux artefacts. Le superviseur de
code en est l'exemple : son cœur est un hook, il embarque un sous-agent et une skill, et il est
distribué comme plugin — donc il vit dans `plugins/`, et ses composants vivent **avec lui**, pas
dispersés dans les dossiers correspondants.

Corollaire : les dossiers de premier niveau ne contiennent que des artefacts **autonomes**. Un
sous-agent livré par un plugin n'a rien à faire dans `agents/`.

---

## Vue d'ensemble

```text
ai-toolkit-registry/
├── .claude-plugin/   → déclaration des plugins du dépôt (marketplace)
├── agents/           → sous-agents autonomes
├── commands/         → commandes slash
├── docs/             → documentation du dépôt
├── hooks/            → hooks autonomes
├── instructions/     → gabarits de contexte projet
├── mcp/              → configurations de serveurs MCP
├── output-styles/    → styles de sortie
├── plugins/          → plugins Claude Code
├── schemas/          → schéma de validation des métadonnées
├── skills/           → skills, par catégorie fonctionnelle
├── templates/        → un gabarit par type d'artefact
└── tools/            → validation et génération de l'index
```

Chaque dossier de type porte un `README.md` qui explique le type, sa forme attendue et son
installation. Ces fichiers sont la documentation de référence du type ; ce document-ci ne décrit que
l'ossature.

---

## Deux formes d'artefact

| Forme | Types concernés | Métadonnées |
|-------|-----------------|-------------|
| **Dossier** | skill, plugin, hook, instructions, serveur MCP | `metadata.yaml` + `README.md` obligatoires |
| **Mono-fichier** | sous-agent, commande, style de sortie | front matter du fichier lui-même |

La forme mono-fichier existe parce que ces trois types *sont* un seul fichier Markdown à front
matter : leur imposer un `metadata.yaml` à côté créerait la même information à deux endroits, et le
fichier ne serait plus directement copiable vers `~/.claude/`.

Le nom de l'artefact est le nom du dossier, ou le nom du fichier sans extension. Le champ `name`
doit lui être égal — le validateur le vérifie.

---

## Catégories

Seul `skills/` est découpé par catégorie fonctionnelle, parce que c'est le dossier qui grossira le
plus : `skills/<catégorie>/<nom>/`. Le champ `category` des métadonnées doit être égal au nom du
dossier parent.

Les autres types sont à plat. Leur champ `category` reste renseigné — il sert au catalogue et à la
recherche — mais il n'influence pas le chemin.

Créer une catégorie de skill est permis : il suffit de créer le dossier et de l'ajouter au tableau
ci-dessous.

| Catégorie | Contenu |
|-----------|---------|
| `development/` | développement logiciel : revue, génération, empaquetage |
| `documentation/` | rédaction et documentation technique |
| `refactoring/` | restructuration et amélioration de code existant |
| `testing/` | tests, couverture, qualité |
| `analysis/` | analyse de code, d'architecture, de données |

Une catégorie sans artefact n'existe pas dans l'arborescence : git ne versionne pas les dossiers
vides, et un `.gitkeep` par catégorie éventuelle serait du bruit. On crée la catégorie avec son
premier artefact.

---

## `.claude-plugin/`

Contient `marketplace.json`, qui déclare les plugins hébergés par ce dépôt. La racine de la
marketplace est le répertoire qui contient ce fichier, et les chemins `source` y sont relatifs — un
plugin n'a donc pas besoin d'être à la racine du dépôt.

Un plugin déclare son propre contenu dans `plugins/<nom>/.claude-plugin/plugin.json`, et ses hooks
dans `plugins/<nom>/hooks/hooks.json`. Le chemin racine du plugin installé est fourni à l'exécution
par `${CLAUDE_PLUGIN_ROOT}` : aucun chemin absolu ne doit apparaître dans ces fichiers.

Le validateur vérifie que tout plugin présent dans `plugins/` est déclaré dans la marketplace, et
réciproquement.

---

## `schemas/`

`artifact.schema.json` (JSON Schema draft-07) valide les métadonnées de **tous** les types. Le champ
`kind` y est obligatoire et son énumération est la liste des types : ajouter un type au registre
commence par là.

---

## `templates/`

Un gabarit par type d'artefact. Un nouvel artefact part toujours d'une copie de son gabarit, ce qui
garantit que les fichiers obligatoires existent et que les métadonnées sont complètes.

---

## `tools/`

`validate.py` et `generate_index.py`. Ce qu'ils vérifient et produisent est décrit dans
[`tools/README.md`](../tools/README.md). Ils n'ont besoin que de PyYAML, et utilisent `jsonschema`
s'il est disponible.

---

## Ajouter un type d'artefact au registre

Le jour où Claude Code introduit un mécanisme de plus :

1. Ajouter sa valeur à l'énumération `kind` de `schemas/artifact.schema.json`.
2. Ajouter son entrée dans le dictionnaire `KINDS` de `tools/validate.py` : dossier, forme
   (`dir` ou `file`), fichiers obligatoires.
3. Ajouter son libellé dans `KIND_LABEL` et `KIND_ORDER` de `tools/generate_index.py`.
4. Créer le dossier avec son `README.md`, et le gabarit dans `templates/`.
5. Ajouter la ligne correspondante au tableau du `README.md` racine et à ce document.
6. Lancer `python tools/validate.py --self-test` puis `python tools/validate.py`.
