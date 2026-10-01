# Commandes

Une **commande** est un raccourci que vous tapez : `/ma-commande`. Elle injecte un prompt
paramétrable dans la session courante. Pas de contexte séparé, pas de délégation — c'est du texte
prêt à l'emploi, pour une tâche que vous répétez.

À distinguer de ses voisines : une skill, c'est Claude qui décide de la charger ; une commande,
c'est vous qui l'invoquez ; un sous-agent travaille à côté, dans son propre contexte.

## Forme attendue

Artefact **mono-fichier** : `commands/<nom>.md`. Métadonnées dans le front matter.

```markdown
---
kind: command
name: ma-commande
displayName: Ma Commande
description: Ce que fait la commande.
version: 1.0.0
status: stable
category: development
tags: [git]
compatibility: [claude-code, claude-desktop]
authors: [Fabrice Turleque]
license: MIT
argument-hint: <branche>
allowed-tools: Bash(git status:*), Bash(git diff:*)
---

Le corps est le prompt. `$ARGUMENTS` reçoit ce qui suit la commande,
`$1`, `$2` les arguments positionnels.
Une ligne commençant par `!` est une commande shell exécutée avant,
dont la sortie est injectée dans le prompt.
```

## Installation

| Portée | Emplacement | Invocation |
|--------|-------------|-----------|
| Tous vos projets | `~/.claude/commands/<nom>.md` | `/<nom>` |
| Un seul projet | `<projet>/.claude/commands/<nom>.md` | `/<nom>` |

```bash
cp commands/ma-commande.md ~/.claude/commands/
```

Une commande livrée par un plugin s'invoque `/<plugin>:<commande>`.
