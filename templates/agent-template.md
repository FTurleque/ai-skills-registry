---
kind: agent
name: agent-template
displayName: Nom du Sous-agent
description: Ce que fait l'agent et dans quelles situations le déléguer. Ce champ décide de la délégation automatique.
version: 1.0.0
status: draft
category: development
tags:
  - tag1
compatibility:
  - claude-code
  - claude-desktop
authors:
  - Fabrice Turleque
license: MIT
tools: Read, Grep, Glob
model: sonnet
---

Tu es <rôle>. Décrire la posture, pas la tâche du jour : cet agent sera appelé dans des contextes
variés.

## Méthode

1. Première étape, avec la commande ou l'outil à utiliser.
2. Deuxième étape.
3. Vérifier avant de conclure : dire quoi.

## Contraintes

- Ce que l'agent ne doit jamais faire.
- Ce qu'il doit toujours faire.
- S'il ne doit pas modifier de fichier, ne pas lui donner `Write` ni `Edit` dans `tools` : une
  interdiction outillée vaut mieux qu'une interdiction écrite.

## Restitution

La forme exacte de ce que l'agent rend. Un agent dont la sortie n'est pas cadrée est inexploitable
par l'agent appelant.
