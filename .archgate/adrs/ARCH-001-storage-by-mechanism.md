---
id: ARCH-001
title: Ranger les artefacts par mécanisme, pas par sujet
domain: architecture
rules: false
files: ["skills/**", "plugins/**", "agents/**", "commands/**", "hooks/**", "instructions/**", "mcp/**", "output-styles/**", "templates/**"]
---

# Ranger les artefacts par mécanisme, pas par sujet

## Context

Le registre héberge huit types d'artefacts pour Claude. Un même besoin — une revue de code, par exemple — peut prendre la forme d'une skill, d'un sous-agent, d'un plugin, ou des trois à la fois : classer par sujet ne dit pas où ranger un artefact ni comment il s'installe.

Fait établi : la règle et ses raisons sont écrites dans [docs/architecture.md](../../docs/architecture.md), sections « La règle de rangement » et « Vue d'ensemble ». Elle est entrée dans le dépôt avec le commit `3a04400` du 2026-10-02 (« Restructure le registre par type d'artefact »).

**Alternatives :** aucune étude n'est consignée dans le dépôt. Le commit `3a04400` restructure une organisation antérieure ; ses raisons ne sont pas documentées au-delà de ce que dit `docs/architecture.md`. Question ouverte : quelles options ont été écartées à l'époque.

## Decision

**Statut : acceptée (2026-10-10).** Reprise d'une règle déjà en vigueur dans `docs/architecture.md` ; acceptée comme ADR par le mainteneur le 2026-10-10. Responsable : Fabrice Turleque.

- Le dossier de premier niveau d'un artefact MUST être celui de son mécanisme d'exécution : `skills/`, `plugins/`, `agents/`, `commands/`, `hooks/`, `instructions/`, `mcp/`, `output-styles/`.
- Le champ `kind` MUST correspondre à ce dossier.
- Les composants d'un plugin MUST vivre dans le plugin ; les dossiers de premier niveau ne contiennent que des artefacts autonomes.
- Un artefact qui semble relever de deux dossiers est traité comme deux artefacts.
- Seul `skills/` est découpé par catégorie fonctionnelle ; les autres types sont à plat.

Périmètre : tous les dossiers d'artefacts et `templates/`. Hors périmètre : `docs/`, `tools/`, `schemas/`, la configuration du dépôt.

## Do's and Don'ts

### Do
- Choisir le type avant d'écrire, avec le tableau de `docs/architecture.md`.
- Partir du gabarit du type dans `templates/`.

### Don't
- Ne pas ranger dans `agents/` ou `skills/` un composant livré par un plugin.
- Ne pas créer de dossier de premier niveau par sujet.

## Consequences

### Positive
- L'emplacement d'un artefact dit comment il s'exécute et s'installe.
- Un plugin s'installe et se retire d'un bloc.

### Negative
- Des artefacts d'un même sujet sont dispersés ; le sujet se retrouve par `INDEX.md`, les catégories et les tags.
- Ajouter un type d'artefact touche le schéma, le validateur, le générateur d'index et les gabarits.

### Risks
- Changer de règle déplacerait les artefacts publiés ; pour un plugin, le chemin fait partie de l'installation.

## Compliance and Enforcement

### Automated Enforcement
- `python tools/validate.py` : `kind` cohérent avec le dossier de premier niveau, `name` égal au dossier, `category` égal au dossier parent pour une skill, plugins déclarés dans la marketplace et réciproquement. Exécuté par la CI (`.github/workflows/validate.yml`).
- Aucune règle Archgate : le validateur couvre déjà ces contraintes, elles ne sont pas dupliquées.

### Manual Enforcement
- Le **choix du type** lui-même (le validateur vérifie la cohérence, pas la pertinence).
- L'absence, dans un dossier de premier niveau, d'un composant qui devrait vivre dans un plugin.

## References

- [docs/architecture.md](../../docs/architecture.md) — règle, vue d'ensemble, ajout d'un type
- [docs/contributing.md](../../docs/contributing.md) — choisir le type
- [ARCH-002](ARCH-002-single-metadata-schema.md)
