---
name: exemple
description: Sous-agent livre par ce plugin. Supprimer ce fichier si le plugin n'en fournit pas.
tools: Read, Grep, Glob
model: sonnet
---

Le corps est le prompt systeme de l'agent.

Un sous-agent livre par un plugin s'invoque `@<plugin>:<agent>`. Ses metadonnees sont celles de
Claude Code : il n'a pas besoin des champs du registre, qui sont portes par le `metadata.yaml` du
plugin.
