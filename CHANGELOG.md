# Changelog

Toutes les modifications notables de ce dépôt sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet respecte le [Versionnement Sémantique](https://semver.org/lang/fr/).

---

## [Non publié]

### Modifié — rapports du superviseur de code

- Les rapports et l'état anti-boucle s'écrivent désormais dans `<projet>/docs/rapport-supervisor/`
  et non plus dans `<projet>/.claude/supervisor/`. Le dossier porte son propre `.gitignore` (`*`) :
  les rapports ne sont jamais commités. Un moteur déjà installé doit être réinstallé pour en profiter.
- Ajout de `.claude/CLAUDE.md` et `.claude/settings.json` : configuration Claude partagée du dépôt.

### Modifié — restructuration du dépôt

Le dépôt s'appelait `ai-skills-registry` et rangeait tout sous `skills/`, y compris ce qui n'est pas
une skill. Chaque dossier de premier niveau porte désormais **un type d'artefact**, et son nom dit ce
que l'artefact est.

- Dépôt et marketplace renommés `ai-toolkit-registry`. Le nom de la marketplace est le suffixe
  d'installation des plugins : il passe de `@ai-skills-registry` à `@ai-toolkit-registry`, et une
  marketplace déjà ajoutée doit être retirée puis rajoutée.
- Nouvelle arborescence par type : `skills/`, `plugins/`, `agents/`, `commands/`, `hooks/`,
  `instructions/`, `mcp/`, `output-styles/`. Chacun porte un `README.md` qui documente le type, sa
  forme attendue et son installation.
- Le niveau `skills/shared/` est supprimé : la portabilité est déclarée par le champ `compatibility`,
  l'encoder aussi dans le chemin faisait la même information à deux endroits. Les skills vivent
  maintenant sous `skills/<catégorie>/<nom>/`.
- Les dossiers `skills/copilot/`, `skills/chatgpt/` et `skills/opencode/` sont supprimés. Le registre
  cible Claude et ses surfaces ; les autres assistants ne sont plus une dimension du dépôt.
- `schemas/skill.schema.json` devient `schemas/artifact.schema.json` et valide **tous** les types. Le
  champ `kind` devient obligatoire, le champ `compatibility` prend pour valeurs les surfaces Claude
  (`claude-code`, `claude-desktop`, `claude-ai`, `claude-api`), et les champs facultatifs `requires`,
  `homepage` et `replaces` apparaissent.
- `docs/compatibility.md` devient `docs/surfaces.md` : surfaces Claude au lieu d'outils IA.
- Nouveau `docs/install.md` : comment consommer chaque type d'artefact, par surface et par portée.
- Un gabarit par type dans `templates/`.

### Ajouté

- Plugin `code-supervisor` (`plugins/code-supervisor/`) : supervision automatique du code produit par
  un agent Claude Code. Hooks `Stop` et `SubagentStop`, moteur d'analyse statique portable sans
  dépendance (sécurité, bugs introduits, duplication, complexité, nommage, conventions), relecture
  par modèle via `claude -p`, et renvoi de l'agent en correction sur un constat bloquant. Installable
  comme plugin, et installable à la main.
- Le dépôt est une marketplace de plugins Claude Code : `.claude-plugin/marketplace.json` à la
  racine.
- Outillage du dépôt : `tools/validate.py` (métadonnées contre schéma, cohérence `kind` / chemin /
  `name` / `category`, fichiers obligatoires, front matter synchronisé avec `metadata.yaml`,
  manifestes de plugin et marketplace, absence de chemin absolu et de secret, index à jour) avec son
  `--self-test`, et `tools/generate_index.py` qui produit `INDEX.md`.
- `INDEX.md` : catalogue généré de tous les artefacts, par type.
- Workflow GitHub `validate` : auto-test du validateur, validation du registre, vérification de
  l'index et auto-tests des moteurs livrés, sur chaque pull request.
- Skill `generate-windows-exe` (`skills/development/generate-windows-exe/`) : génération d'un
  exécutable Windows via Inno Setup ou jpackage, avec un driver PowerShell reproductible.

### Déplacé

- `skills/shared/development/java-code-review/` → `skills/development/java-code-review/` (version
  1.1.0 : métadonnées au nouveau schéma)
- `skills/shared/development/generate-windows-exe/` → `skills/development/generate-windows-exe/`
  (version 1.1.0 : métadonnées au nouveau schéma)
- `skills/claude/code-supervisor/` → `plugins/code-supervisor/`

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
