# Index du registre

Catalogue de tous les artefacts du depot, par type.

> Fichier genere par `python tools/generate_index.py`. Ne pas l'editer a la main.

## Resume

| Type | Nombre |
|------|-------:|
| Skills | 8 |
| Plugins | 1 |
| Sous-agents | 0 |
| Commandes | 0 |
| Hooks | 0 |
| Instructions de projet | 0 |
| Serveurs MCP | 0 |
| Styles de sortie | 0 |
| **Total** | **9** |

## Skills

| Artefact | Description | Version | Statut | Surfaces |
|----------|-------------|---------|--------|----------|
| [`adr-audit`](skills/architecture/adr-audit) | Audite l'ensemble des ADR (Architecture Decision Records) d'un projet et leur cohérence avec le dossier arc42, les changements OpenSpec et le code : inventai... | 1.0.0 | experimental | Code |
| [`adr-author`](skills/architecture/adr-author) | Décide si un ADR (Architecture Decision Record) est justifié, puis crée ou améliore le bon document, à partir d'un besoin, d'un changement OpenSpec ou d'une ... | 1.0.0 | experimental | Code |
| [`adr-check`](skills/architecture/adr-check) | Contrôle le respect des ADR (Architecture Decision Records) dans le code et la cohérence documentaire. Deux modes : contrôle d'un changement (diff, branche, ... | 1.0.0 | experimental | Code |
| [`adr-policy`](skills/architecture/adr-policy) | Ressources partagées par les skills adr-audit, adr-author et adr-check : politique de pertinence des ADR, découverte du contexte d'un projet, articulation av... | 1.0.0 | experimental | Code |
| [`audit-application`](skills/development/audit-application) | Audit de code complet d'une application (architecture, qualité, sécurité, tests, performance, dépendances, CI/CD) produisant un rapport versionné dans le dép... | 1.0.0 | experimental | Code, Desktop |
| [`code-to-openspec`](skills/development/code-to-openspec) | Rétro-ingénierie d'une application existante à partir de son code, puis préparation de changements OpenSpec traçables (constats, exigences, scénarios, tâches... | 1.0.0 | experimental | Code, Desktop |
| [`generate-windows-exe`](skills/development/generate-windows-exe) | Empaquette une application en executable Windows (.exe) via Inno Setup ou jpackage, avec un driver reproductible. | 1.1.0 | stable | Code, Desktop |
| [`java-code-review`](skills/development/java-code-review) | Analyse du code Java afin d'identifier les défauts, risques et améliorations possibles. | 1.1.0 | stable | Code, Desktop, claude.ai, API |

## Plugins

| Artefact | Description | Version | Statut | Surfaces |
|----------|-------------|---------|--------|----------|
| [`code-supervisor`](plugins/code-supervisor) | Supervision automatique du code produit par un agent, avec renvoi en correction sur probleme bloquant. | 1.2.0 | experimental | Code, Desktop |
