# Architecture du dépôt

Ce document décrit l'organisation du dépôt **AI Skills Registry** et le rôle de chaque dossier.

---

## Vue d'ensemble

Le dépôt est structuré en plusieurs couches :

```text
ai-skills-registry/
├── skills/       → Skills organisés par portée et catégorie
├── templates/    → Modèles pour créer de nouveaux skills
├── schemas/      → Schémas de validation des métadonnées
├── docs/         → Documentation du dépôt
└── tools/        → Utilitaires éventuels (scripts, outils)
```

---

## Séparation `shared` / dossiers fournisseurs

### `skills/shared/`

Contient les skills **génériques et réutilisables**, indépendants d'un outil IA spécifique. Ces skills peuvent fonctionner avec n'importe quel assistant compatible.

Ils sont organisés par catégorie fonctionnelle :

| Catégorie       | Description                                  |
|-----------------|----------------------------------------------|
| `development/`  | Développement logiciel (revues, génération…) |
| `documentation/`| Rédaction et documentation technique         |
| `refactoring/`  | Restructuration et amélioration du code      |
| `testing/`      | Tests, couverture, qualité                   |
| `analysis/`     | Analyse de code, d'architecture, de données  |

### `skills/copilot/`, `skills/claude/`, `skills/chatgpt/`, `skills/opencode/`

Contiennent les skills **spécifiques à un fournisseur** ou adaptés à ses capacités particulières (syntaxe, format, limites).

Un skill fournisseur peut :
- Être une adaptation d'un skill générique
- Exploiter des fonctionnalités propres à l'outil (ex. agents, actions, tools)
- Référencer un skill partagé dans sa documentation

---

## Rôle de chaque dossier

### `templates/`

Contient le **template de référence** pour créer un nouveau skill. Chaque nouveau skill doit être basé sur `templates/skill-template/`.

### `schemas/`

Contient le **schéma JSON** (`skill.schema.json`) permettant de valider les métadonnées d'un skill. Ce schéma peut être utilisé par des outils d'automatisation ou des pipelines CI.

### `docs/`

Documentation du dépôt lui-même :

- `architecture.md` — ce fichier
- `conventions.md` — règles de nommage et de rédaction
- `compatibility.md` — matrice de compatibilité par outil
- `contributing.md` — processus de contribution détaillé

### `tools/`

Répertoire prévu pour accueillir des scripts ou utilitaires liés au dépôt (validation, génération, etc.). Actuellement vide ou documenté dans `tools/README.md`.

---

## Fonctionnement des templates

Le dossier `templates/skill-template/` contient la structure minimale d'un skill :

```text
skill-template/
├── SKILL.md        → Instructions principales (front matter YAML + corps Markdown)
├── metadata.yaml   → Métadonnées exploitables par un outil externe
├── README.md       → Présentation lisible du skill
├── examples/       → Exemples d'utilisation
└── resources/      → Ressources annexes (.gitkeep si vide)
```

Pour créer un nouveau skill, copier ce dossier, le renommer et remplir les fichiers.

---

## Rôle des schémas

Le fichier `schemas/skill.schema.json` définit le schéma JSON Schema (draft-07) des métadonnées d'un skill.

Il permet de :
- Valider la structure d'un `metadata.yaml` ou d'un front matter
- Détecter les erreurs de nommage, de version ou de valeurs invalides
- Automatiser la vérification dans un pipeline CI/CD

---

## Adapter un skill générique à plusieurs assistants IA

1. Créer ou identifier le skill dans `skills/shared/<categorie>/<nom-du-skill>/`
2. Vérifier sa compatibilité dans son front matter (`compatibility`)
3. Si une adaptation est nécessaire pour un outil précis, créer un skill dédié dans `skills/<fournisseur>/<nom-du-skill>/`
4. Le skill fournisseur peut référencer le skill partagé dans son `README.md`
5. Documenter les différences dans `docs/compatibility.md`
