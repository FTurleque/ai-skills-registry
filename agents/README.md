# Sous-agents

Un **sous-agent** est un assistant spécialisé que Claude peut déléguer, ou que vous appelez
explicitement. Il a son propre prompt système, sa propre liste d'outils autorisés et son propre
contexte : ce qu'il lit n'encombre pas la conversation principale.

Les sous-agents de ce dossier sont **autonomes** : ils ne dépendent d'aucun plugin. Un sous-agent
livré par un plugin vit dans le dossier de ce plugin, pas ici.

## Forme attendue

Un sous-agent est un artefact **mono-fichier** : `agents/<nom>.md`. Ses métadonnées sont dans son
front matter — pas de `metadata.yaml` séparé, qui ferait la même information à deux endroits.

```markdown
---
kind: agent
name: mon-agent
displayName: Mon Agent
description: Ce que fait l'agent et quand le déléguer.
version: 1.0.0
status: stable
category: development
tags: [review]
compatibility: [claude-code, claude-desktop]
authors: [Fabrice Turleque]
license: MIT
tools: Read, Grep, Glob, Bash
model: sonnet
---

Le corps du fichier est le prompt système de l'agent.
```

Les champs `kind`, `name`, `displayName`, `description`, `version`, `status`, `category`, `tags`,
`compatibility`, `authors` et `license` sont ceux du registre. Les champs `tools`, `model`,
`disallowedTools`, `permissionMode`, `maxTurns`, `skills` et les autres sont ceux de Claude Code :
ils sont ignorés par le registre et lus par l'outil.

## Installation

| Portée | Emplacement |
|--------|-------------|
| Tous vos projets | `~/.claude/agents/<nom>.md` |
| Un seul projet | `<projet>/.claude/agents/<nom>.md` |

```bash
cp agents/mon-agent.md ~/.claude/agents/
```

Puis dans une session : `@mon-agent relis mes modifications`.

## Écrire un bon sous-agent

- La `description` décide de la délégation automatique : dire quand l'utiliser.
- Restreindre `tools` au nécessaire. Un agent de relecture n'a pas besoin de `Write` ni de `Edit`,
  et le lui refuser garantit qu'il ne modifiera rien.
- Un prompt système, pas une consigne de tâche : l'agent sera appelé dans des contextes variés.
