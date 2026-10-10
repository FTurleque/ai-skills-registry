---
kind: skill
name: adr-policy
displayName: Politique ADR (ressources partagées)
description: >-
  Ressources partagées par les skills adr-audit, adr-author et adr-check : politique de pertinence
  des ADR, découverte du contexte d'un projet, articulation avec arc42 et OpenSpec, usage vérifié
  d'Archgate CLI, gabarits d'ADR et de restitution, script d'inventaire. Ne se déclenche pas seul
  et ne s'invoque pas : il est lu par les trois autres skills, qui ne fonctionnent pas sans lui.
version: 1.0.0
status: experimental
category: architecture
tags:
  - adr
  - architecture
  - policy
  - arc42
  - openspec
  - archgate
compatibility:
  - claude-code
requires:
  - python>=3.8 (script facultatif)
authors:
  - Fabrice Turleque
license: MIT
user-invocable: false
disable-model-invocation: true
---

# Politique ADR — ressources partagées

Ce dossier ne fait rien par lui-même. Il porte, en un seul exemplaire, ce que `adr-audit`, `adr-author` et `adr-check` ont en commun, pour qu'il n'en existe pas trois copies divergentes.

Il s'installe **à côté** des trois skills, dans le même dossier `skills/` : ils le lisent par le chemin relatif `../adr-policy/resources/`.

| Fichier | Contenu | Lu quand |
|---|---|---|
| `resources/policy.md` | filtre de pertinence, cinq conclusions possibles, statuts, validation humaine, préservation de l'historique, étiquettes de preuve | toujours |
| `resources/discovery.md` | quoi découvrir dans le projet courant, quoi faire quand un composant manque | toujours |
| `resources/arc42-openspec.md` | index en section 9, sections à revoir par type d'impact, revue d'impact architectural, contrôle avant archivage | dès qu'arc42 ou OpenSpec est en jeu |
| `resources/archgate.md` | commandes, format d'ADR et de règle, **sélection par diff et faux verts**, initialisation sans plugin — vérifié par exécution | dès qu'Archgate est en jeu |
| `resources/verification.md` | rendre une décision vérifiable, choisir le contrôle, trois catégories de résultat | rédaction de la vérification, contrôle |
| `resources/templates/adr.md` | gabarit d'ADR (variante Archgate, variante Markdown), procédure de remplacement | rédaction |
| `resources/templates/reports.md` | restitutions des trois skills | restitution |
| `resources/adr_tool.py` | `inventory` et `check` : emplacements, statuts déclarés, doublons, liens cassés, index arc42 (Python 3.8+, facultatif) | inventaire, contrôle documentaire |

Rien ici ne nomme un projet, un module ou une technologie imposée : les conventions d'un projet vivent dans son dépôt et priment sur cette politique générale quand elles sont plus précises.
