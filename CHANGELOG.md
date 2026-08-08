# Changelog

Toutes les modifications notables de ce dépôt sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet respecte le [Versionnement Sémantique](https://semver.org/lang/fr/).

---

## [Non publié]

### Ajouté

- Skill `generate-windows-exe` (`skills/shared/development/generate-windows-exe/`) :
  génération d'un executable Windows (`.exe`) via Inno Setup (installateur) ou
  jpackage (lanceur natif Java), avec un driver PowerShell reproductible
  (`resources/build-exe.ps1`) et un modèle Inno Setup. Distillé des pipelines
  réels de `mcp-search-net` et `nexus-context-engine`.

---

## [0.1.0] - 2026-07-02

### Ajouté

- Création de l'architecture initiale du registre de skills IA
- Structure de dossiers : `skills/`, `docs/`, `schemas/`, `templates/`, `tools/`
- Schéma JSON de validation des métadonnées (`schemas/skill.schema.json`)
- Template de skill réutilisable (`templates/skill-template/`)
- Skill d'exemple : `skills/shared/development/java-code-review/`
- Documentation principale : `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Documentation technique : `docs/architecture.md`, `docs/conventions.md`, `docs/compatibility.md`, `docs/contributing.md`
- Modèles GitHub : templates d'issues et de pull request
- Fichiers de configuration Git : `.gitignore`, `.editorconfig`, `.gitattributes`
- Licence MIT

[0.1.0]: https://github.com/FTurleque/ai-skills-registry/releases/tag/v0.1.0
