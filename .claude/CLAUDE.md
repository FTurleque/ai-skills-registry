# AI Toolkit Registry

Registre d'artefacts pour Claude (skills, plugins, sous-agents, commandes, hooks, instructions,
serveurs MCP, styles de sortie). Les règles complètes sont dans `docs/` : ce fichier n'en garde que
l'essentiel pour travailler ici.

## Où va un artefact

Le dossier dit le mécanisme, pas le sujet (`docs/architecture.md`). Un artefact par type et par
dossier de premier niveau : `skills/`, `plugins/`, `agents/`, `commands/`, `hooks/`,
`instructions/`, `mcp/`, `output-styles/`. Les composants d'un plugin vivent **dans** le plugin.

## Conventions (`docs/conventions.md`)

- Dossiers et fichiers en anglais, documentation en français.
- Noms d'artefacts en kebab-case ; `name` égal au nom du dossier ; `kind` égal au dossier de premier niveau.
- Les fichiers standards gardent leur nom exact : `SKILL.md`, `metadata.yaml`, `README.md`, `plugin.json`, `hooks.json`.
- Renommer un artefact publié : renseigner `replaces`, mettre à jour `CHANGELOG.md`, version majeure si l'installation casse.
- Un nouvel artefact part du gabarit correspondant dans `templates/`.

## Commandes

```bash
python tools/validate.py              # valide le dépôt (doit afficher « Aucun probleme »)
python tools/validate.py --self-test  # auto-test du validateur
python tools/generate_index.py        # régénère INDEX.md
python tools/generate_index.py --check
claude plugin validate . --strict     # marketplace
claude plugin validate ./plugins/<nom> --strict
```

Après tout ajout ou modification d'artefact : valider, régénérer `INDEX.md`, mettre à jour
`CHANGELOG.md`. La CI (`.github/workflows/validate.yml`) rejoue ces contrôles.

## Rapports du superviseur

Le superviseur écrit ses rapports dans `docs/rapport-supervisor/` (jamais commité : dossier ignoré,
y compris par son propre `.gitignore`). Rien de généré ne doit atterrir dans `.claude/`, qui ne
contient que la configuration versionnée (`CLAUDE.md`, `settings.json`).

## À ne pas faire

- Ne pas modifier le validateur pour faire passer un artefact : corriger la cause.
- Ne jamais mettre de secret en valeur littérale (utiliser une variable d'environnement).
- Ne pas ajouter de suppression d'avertissement (`# noqa`, `@SuppressWarnings`) pour faire taire un contrôle.

## À propos de `.github/`

Ce dossier ne contient pas de configuration IA : GitHub impose cet emplacement pour les gabarits
d'issues, le gabarit de pull request et les workflows CI. La configuration de Claude pour ce dépôt
vit dans `.claude/`.
