# AI Toolkit Registry

Un registre versionné de ce qui outille Claude au quotidien : skills, plugins, sous-agents,
commandes, hooks, instructions de projet, serveurs MCP et styles de sortie.

---

## Le principe

Chaque dossier de premier niveau porte **un type d'artefact**, et son nom dit ce que l'artefact
est. Pas de dossier fourre-tout, pas de nom qui en recouvre un autre.

| Dossier | Type | Ce que c'est | Qui le déclenche |
|---------|------|--------------|------------------|
| [`skills/`](skills/) | skill | un fichier d'instructions que Claude charge quand la tâche s'y prête | Claude, de lui-même |
| [`plugins/`](plugins/) | plugin | un paquet installable qui branche des composants sur Claude Code | l'installation, puis les événements |
| [`agents/`](agents/) | sous-agent | un assistant spécialisé, avec son contexte et ses outils | vous, ou Claude par délégation |
| [`commands/`](commands/) | commande | un raccourci `/nom` qui injecte un prompt prêt à l'emploi | vous |
| [`hooks/`](hooks/) | hook | du code exécuté à un événement de session | l'événement, sans être appelé |
| [`instructions/`](instructions/) | instructions | les gabarits de `CLAUDE.md` et `AGENTS.md` d'un projet | l'ouverture d'une session |
| [`mcp/`](mcp/) | serveur MCP | la configuration pour brancher des outils externes | le démarrage de la session |
| [`output-styles/`](output-styles/) | style de sortie | une posture de réponse, active en permanence | vous, en le sélectionnant |

Le catalogue complet, avec versions et statuts, est dans [INDEX.md](INDEX.md) — généré, jamais
édité à la main.

## Pourquoi ces huit types et pas un seul dossier

Parce qu'ils ne se ressemblent pas. Une skill est du texte que Claude décide de lire. Un hook est du
code qui s'exécute sans que personne le demande. Confondre les deux, c'est se tromper sur ce qui va
se passer — et c'est exactement ce qu'un registre doit empêcher.

La règle de rangement est donc : **le dossier dit le mécanisme, pas le sujet**. Un outil de revue de
code peut être une skill, un sous-agent, un plugin ou les trois ; ce qui décide de son emplacement,
c'est la façon dont il s'exécute.

---

## Portée : Claude

Ce registre cible Claude et ses surfaces : Claude Code, l'application de bureau, claude.ai et
l'API. Chaque artefact déclare les surfaces sur lesquelles il fonctionne dans son champ
`compatibility`. La matrice et les règles sont dans [docs/surfaces.md](docs/surfaces.md).

---

## Installer quelque chose depuis ce dépôt

Les plugins s'installent en deux commandes, parce que le dépôt est aussi une marketplace :

```bash
claude plugin marketplace add FTurleque/ai-toolkit-registry
claude plugin install code-supervisor@ai-toolkit-registry
```

Les skills s'installent par copie, avec vérification de la copie contre le dépôt :

```bash
python tools/install_skill.py install git-submodule-common publish-git-submodule install-git-submodule
python tools/install_skill.py check git-submodule-common publish-git-submodule install-git-submodule
```

Les autres types se copient à la main, chacun à son emplacement. La procédure complète, type par
type et surface par surface, est dans [docs/install.md](docs/install.md).

Ces skills-là partagent un dépôt ou un dossier entre plusieurs dépôts par sous-module, et le
tiennent à jour par GitHub Actions : [docs/git-submodule-sync.md](docs/git-submodule-sync.md).

---

## Arborescence

```text
ai-toolkit-registry/
├── .claude-plugin/
│   └── marketplace.json        déclaration des plugins du dépôt
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/validate.yml  validation à chaque PR
├── agents/                     sous-agents autonomes (<nom>.md)
├── commands/                   commandes slash (<nom>.md)
├── docs/
│   ├── architecture.md         organisation du dépôt, rôle de chaque dossier
│   ├── conventions.md          règles de nommage, de rédaction et d'hygiène
│   ├── surfaces.md             surfaces Claude et matrice de compatibilité
│   ├── install.md              comment consommer chaque type d'artefact
│   ├── git-submodule-sync.md   partager un dépôt ou un dossier par sous-module
│   └── contributing.md         processus de contribution détaillé
├── hooks/                      hooks autonomes (<nom>/)
├── instructions/               gabarits de contexte projet (<nom>/)
├── mcp/                        configurations de serveurs MCP (<nom>/)
├── output-styles/              styles de sortie (<nom>.md)
├── plugins/                    plugins Claude Code (<nom>/)
├── schemas/
│   └── artifact.schema.json    schéma des métadonnées, tous types confondus
├── skills/
│   └── <catégorie>/<nom>/      skills, par catégorie fonctionnelle
├── templates/                  un gabarit par type d'artefact
├── tools/
│   ├── validate.py             validation du registre
│   ├── generate_index.py       génération d'INDEX.md
│   └── install_skill.py        installation des skills dans ~/.claude/skills/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── INDEX.md                    catalogue généré
├── LICENSE
└── README.md
```

---

## Métadonnées : un seul schéma

Tous les types partagent le même jeu de métadonnées, validé par
[`schemas/artifact.schema.json`](schemas/artifact.schema.json) :

```yaml
kind: skill              # skill | plugin | agent | command | hook | instructions | mcp-server | output-style
name: mon-artefact       # kebab-case, égal au nom du dossier ou du fichier
displayName: Mon Artefact
description: Ce qu'il fait et quand l'utiliser.
version: 1.0.0           # SemVer
status: stable           # draft | experimental | stable | deprecated
category: development
tags: [exemple]
compatibility: [claude-code]
authors: [Fabrice Turleque]
license: MIT
requires: [python>=3.8]  # facultatif
```

Elles vivent dans `metadata.yaml` pour les artefacts en dossier, et dans le front matter du fichier
pour les artefacts mono-fichier (sous-agents, commandes, styles de sortie) — une seule source, pas
deux. Un `SKILL.md` accompagné d'un `metadata.yaml` doit porter exactement les mêmes valeurs : le
validateur refuse une divergence.

---

## Ajouter un artefact

1. Copier le gabarit de son type depuis [`templates/`](templates/).
2. Le placer dans le dossier de son type, sous un nom en kebab-case.
3. Renseigner les métadonnées, rédiger la documentation, ajouter un exemple réel.
4. Valider et régénérer l'index :

```bash
python tools/validate.py
python tools/generate_index.py
```

5. Mettre à jour `CHANGELOG.md` et la matrice de `docs/surfaces.md`.
6. Ouvrir une pull request avec la checklist remplie.

Le détail est dans [docs/contributing.md](docs/contributing.md), les règles dans
[docs/conventions.md](docs/conventions.md).

---

## Validation

```bash
pip install pyyaml jsonschema
python tools/validate.py              # métadonnées, cohérence, hygiène, index
python tools/validate.py --strict     # les avertissements deviennent des erreurs
python tools/validate.py --self-test  # vérifie le validateur lui-même
python tools/generate_index.py --check # échoue si INDEX.md n'est pas à jour
claude plugin validate .              # manifestes de plugin et marketplace
```

Ces mêmes commandes tournent sur chaque pull request. Ce qu'elles vérifient est listé dans
[tools/README.md](tools/README.md).

---

## Versionnement

Chaque artefact porte sa propre version SemVer dans ses métadonnées. Le dépôt est versionné dans
[CHANGELOG.md](CHANGELOG.md) au format [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## Licence

[MIT](LICENSE) — Copyright © 2026 Fabrice Turleque
