# Index du registre

Catalogue de tous les artefacts du depot, par type.

> Fichier genere par `python tools/generate_index.py`. Ne pas l'editer a la main.

## Resume

| Type | Nombre |
|------|-------:|
| Skills | 3 |
| Plugins | 1 |
| Sous-agents | 0 |
| Commandes | 0 |
| Hooks | 0 |
| Instructions de projet | 0 |
| Serveurs MCP | 0 |
| Styles de sortie | 0 |
| **Total** | **4** |

## Skills

| Artefact | Description | Version | Statut | Surfaces |
|----------|-------------|---------|--------|----------|
| [`code-to-openspec`](skills/development/code-to-openspec) | Rétro-ingénierie d'une application existante à partir de son code, puis préparation de changements OpenSpec traçables (constats, exigences, scénarios, tâches... | 1.0.0 | experimental | Code, Desktop |
| [`generate-windows-exe`](skills/development/generate-windows-exe) | Empaquette une application en executable Windows (.exe) via Inno Setup ou jpackage, avec un driver reproductible. | 1.1.0 | stable | Code, Desktop |
| [`java-code-review`](skills/development/java-code-review) | Analyse du code Java afin d'identifier les défauts, risques et améliorations possibles. | 1.1.0 | stable | Code, Desktop, claude.ai, API |

## Plugins

| Artefact | Description | Version | Statut | Surfaces |
|----------|-------------|---------|--------|----------|
| [`code-supervisor`](plugins/code-supervisor) | Supervision automatique du code produit par un agent, avec renvoi en correction sur probleme bloquant. | 1.2.0 | experimental | Code, Desktop |
