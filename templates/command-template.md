---
kind: command
name: command-template
displayName: Nom de la Commande
description: Ce que fait la commande quand on la tape.
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
argument-hint: <argument>
allowed-tools: Bash(git status:*), Bash(git diff:*)
---

Le corps est le prompt injecté dans la session.

- `$ARGUMENTS` reçoit tout ce qui suit la commande.
- `$1`, `$2` reçoivent les arguments positionnels.
- Une ligne commençant par `!` est une commande shell exécutée avant l'envoi, dont la sortie est
  injectée dans le prompt. Elle doit être autorisée par `allowed-tools`.

Exemple :

!git status --porcelain

À partir de l'état ci-dessus, <ce que Claude doit faire> pour $ARGUMENTS.
