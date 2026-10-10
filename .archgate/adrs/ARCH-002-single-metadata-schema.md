---
id: ARCH-002
title: Un schéma de métadonnées unique et fermé, une seule source par artefact
domain: architecture
rules: false
files: ["schemas/**", "skills/**", "plugins/**", "agents/**", "commands/**", "hooks/**", "instructions/**", "mcp/**", "output-styles/**", "templates/**", "tools/**"]
---

# Un schéma de métadonnées unique et fermé, une seule source par artefact

## Context

Le validateur, le générateur d'index et la matrice des surfaces lisent les métadonnées de tous les artefacts, quel que soit leur type. Certains types sont un dossier, d'autres un seul fichier Markdown à front matter.

Faits établis, avec leur source :

- Tous les types partagent un même jeu de métadonnées, validé par `schemas/artifact.schema.json` ; le schéma est fermé (`additionalProperties: false`) — [README.md](../../README.md), section « Métadonnées : un seul schéma », et [docs/conventions.md](../../docs/conventions.md), section « Métadonnées ».
- Deux formes d'artefact, avec la raison écrite : imposer un `metadata.yaml` à un artefact mono-fichier « créerait la même information à deux endroits, et le fichier ne serait plus directement copiable vers `~/.claude/` » — [docs/architecture.md](../../docs/architecture.md), section « Deux formes d'artefact ».
- Pour une skill, `SKILL.md` et `metadata.yaml` portent les mêmes valeurs : « C'est redondant, c'est assumé — le `SKILL.md` sert à l'outil, le `metadata.yaml` à l'outillage du dépôt » — [docs/contributing.md](../../docs/contributing.md), section 3.

Ces règles sont entrées dans le dépôt avec le commit `3a04400` du 2026-10-02.

**Alternatives :** aucune étude n'est consignée (un schéma par type, par exemple). Question ouverte.

## Decision

**Statut : acceptée (2026-10-10).** Reprise de règles déjà en vigueur ; acceptée comme ADR par le mainteneur le 2026-10-10. Responsable : Fabrice Turleque.

- Les métadonnées de tous les types MUST être conformes à l'unique `schemas/artifact.schema.json`. Aucun champ inconnu.
- Un artefact en dossier porte ses métadonnées dans `metadata.yaml` ; un artefact mono-fichier (sous-agent, commande, style de sortie) dans son front matter, et MUST NOT avoir de `metadata.yaml`.
- Exception assumée : une skill porte les mêmes valeurs dans `SKILL.md` et `metadata.yaml` ; toute divergence est une erreur.
- `INDEX.md` est généré depuis ces métadonnées et MUST NOT être édité à la main.

Périmètre : le schéma, tous les artefacts, les gabarits et les deux scripts de `tools/`.

## Do's and Don'ts

### Do
- Ajouter un champ en commençant par le schéma, puis l'outillage.
- Reporter toute modification de version ou de description dans `SKILL.md` **et** `metadata.yaml`.

### Don't
- Ne pas modifier le validateur pour faire passer un artefact.
- Ne pas créer un schéma propre à un type.

## Consequences

### Positive
- Un seul outillage pour valider, indexer et cataloguer tous les types.
- Un artefact mono-fichier reste copiable tel quel.

### Negative
- Une redondance à entretenir pour chaque skill.
- Le front matter d'un `SKILL.md` porte des champs propres au registre, qu'un outil de téléversement plus strict pourrait refuser (non vérifié).

### Risks
- Les champs propres à Claude Code dans un `SKILL.md` (`allowed-tools`, `argument-hint`…) ne sont pas dans `metadata.yaml` : le validateur ne compare que les champs communs.

## Compliance and Enforcement

### Automated Enforcement
- `python tools/validate.py` : conformité au schéma, champs inconnus refusés, égalité `SKILL.md` / `metadata.yaml` sur `kind`, `name`, `version`, `description`, `status`, `compatibility`, identifiant unique. `python tools/validate.py --self-test` éprouve le validateur sur des cas construits.
- `python tools/generate_index.py --check` : `INDEX.md` à jour.
- Les trois sont exécutés par la CI. Aucune règle Archgate : ces contrôles ne sont pas dupliqués.

### Manual Enforcement
- La justesse du contenu des métadonnées (une `description` qui déclenche, un `status` mérité).

## References

- [schemas/artifact.schema.json](../../schemas/artifact.schema.json)
- [tools/README.md](../../tools/README.md) — ce que le validateur vérifie et ne vérifie pas
- [ARCH-001](ARCH-001-storage-by-mechanism.md)
