# AI Skills Registry

Un registre centralisé pour documenter, versionner et réutiliser des skills IA indépendamment du fournisseur.

---

## Présentation

**AI Skills Registry** est un dépôt de configuration et de documentation conçu pour centraliser les skills créés pour différents assistants et agents IA : GitHub Copilot, Claude Code, ChatGPT, OpenCode et tout outil compatible.

Ce dépôt est **indépendant d'un fournisseur précis**. Chaque skill est structuré de manière à pouvoir être réutilisé, adapté et documenté clairement, quelle que soit la plateforme cible.

---

## Objectifs

- Centraliser les skills IA dans un dépôt versionné
- Fournir un format standard et documenté pour chaque skill
- Permettre la réutilisation et l'adaptation entre plusieurs assistants IA
- Maintenir une documentation claire et des conventions cohérentes
- Offrir une bibliothèque de fichiers de configuration prêts à l'emploi

---

## Outils IA ciblés

| Outil            | Identifiant       |
|------------------|-------------------|
| Générique        | `generic`         |
| GitHub Copilot   | `github-copilot`  |
| Claude Code      | `claude-code`     |
| ChatGPT          | `chatgpt`         |
| OpenCode         | `opencode`        |

---

## Arborescence principale

```text
ai-skills-registry/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug-report.md
│   │   └── skill-request.md
│   └── pull_request_template.md
├── docs/
│   ├── architecture.md
│   ├── conventions.md
│   ├── compatibility.md
│   └── contributing.md
├── schemas/
│   └── skill.schema.json
├── skills/
│   ├── shared/
│   │   ├── development/
│   │   ├── documentation/
│   │   ├── refactoring/
│   │   ├── testing/
│   │   └── analysis/
│   ├── copilot/
│   ├── claude/
│   ├── chatgpt/
│   └── opencode/
├── templates/
│   └── skill-template/
│       ├── SKILL.md
│       ├── metadata.yaml
│       ├── README.md
│       ├── examples/
│       └── resources/
├── tools/
│   └── README.md
├── .editorconfig
├── .gitattributes
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Définition d'un skill

Un **skill** est un ensemble structuré d'instructions et de métadonnées qui décrit une tâche ou un comportement attendu d'un assistant IA.

Chaque skill est composé de :

- `SKILL.md` — instructions principales avec front matter YAML
- `metadata.yaml` — métadonnées exploitables par un outil ou script
- `README.md` — présentation lisible du skill
- `examples/` — exemples d'utilisation
- `resources/` — ressources annexes (optionnel)

### Front matter YAML minimal

```yaml
---
name: mon-skill
displayName: Mon Skill
description: Description courte du skill.
version: 1.0.0
status: stable
category: development
tags:
  - exemple
compatibility:
  - generic
authors:
  - Fabrice Turleque
license: MIT
---
```

---

## Ajouter un skill

1. Copier le dossier `templates/skill-template/` dans la catégorie adaptée sous `skills/`
2. Renommer le dossier en kebab-case (ex. `mon-skill`)
3. Renseigner les métadonnées dans `SKILL.md` (front matter) et `metadata.yaml`
4. Rédiger les instructions dans `SKILL.md`
5. Ajouter des exemples dans `examples/`
6. Vérifier la compatibilité avec les outils ciblés
7. Mettre à jour `CHANGELOG.md`
8. Créer une pull request

Voir [docs/contributing.md](docs/contributing.md) pour le détail du processus.

---

## Conventions de nommage

- Noms de dossiers et fichiers en **anglais**
- Noms de skills en **kebab-case** (ex. `java-code-review`)
- Identifiants stables — ne pas renommer un skill déjà publié sans raison
- Documentation principale en **français**

Voir [docs/conventions.md](docs/conventions.md) pour l'ensemble des règles.

---

## Gestion des versions

Ce dépôt utilise le [Versionnement Sémantique](https://semver.org/lang/fr/) (`MAJOR.MINOR.PATCH`).

- Les skills ont leur propre version dans leur `metadata.yaml`
- Le dépôt global est versionné dans `CHANGELOG.md`

---

## Compatibilité entre outils

Chaque skill déclare sa compatibilité dans son front matter via le champ `compatibility`.

La matrice de compatibilité et les explications sont disponibles dans [docs/compatibility.md](docs/compatibility.md).

---

## Exemple minimal

```text
skills/shared/development/java-code-review/
├── SKILL.md
├── metadata.yaml
├── README.md
├── examples/
│   └── example.md
└── resources/
    └── .gitkeep
```

---

## Contribution

Merci de lire [CONTRIBUTING.md](CONTRIBUTING.md) et [docs/contributing.md](docs/contributing.md) avant de soumettre une contribution.

Les contributions doivent respecter les conventions décrites dans [docs/conventions.md](docs/conventions.md).

---

## Licence

Ce dépôt est distribué sous licence [MIT](LICENSE).

Copyright © 2026 Fabrice Turleque