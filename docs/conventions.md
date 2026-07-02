# Conventions du dépôt

Ce document définit les règles et conventions à respecter pour maintenir la cohérence du dépôt **AI Skills Registry**.

---

## Langue

- Les **noms de dossiers et de fichiers** sont en **anglais**
- La **documentation principale** (README, SKILL.md, exemples) est rédigée en **français**
- Les **métadonnées** (champs YAML/JSON) sont en **anglais**

---

## Nommage des fichiers et dossiers

- Les noms de skills utilisent le format **kebab-case** : `java-code-review`, `generate-unit-tests`
- Les noms de dossiers de catégorie sont en minuscules : `development`, `testing`, `analysis`
- Les fichiers standards d'un skill sont toujours nommés de la même façon : `SKILL.md`, `metadata.yaml`, `README.md`
- Les fichiers de configuration racine gardent leur nom conventionnel : `.gitignore`, `.editorconfig`, `LICENSE`

---

## Identifiants stables

- L'identifiant d'un skill correspond au nom de son dossier (ex. `java-code-review`)
- Ne pas renommer un skill déjà publié ou référencé sans mise à jour du changelog et des références
- Les champs `name` dans les métadonnées doivent correspondre exactement au nom du dossier

---

## Documentation lisible

- Chaque skill doit avoir un `README.md` compréhensible sans lire `SKILL.md`
- Les instructions dans `SKILL.md` doivent être claires, complètes et testables
- Les exemples dans `examples/` doivent illustrer un cas d'usage réel ou représentatif

---

## Instructions explicites et testables

- Les instructions d'un skill doivent décrire le comportement attendu de manière précise
- Les entrées et sorties doivent être documentées
- Chaque critère de validation doit être vérifiable (éviter les formulations vagues)

---

## Absence de chemins locaux

- Ne jamais inclure de chemins absolus locaux dans les instructions (`/home/user/...`, `C:\Users\...`)
- Utiliser des chemins relatifs ou des variables conventionnelles (`<project-root>`, `src/`)

---

## Absence de secrets

- Ne jamais inclure de tokens, clés API, mots de passe ou données personnelles dans les fichiers
- Ne pas commettre de fichiers `.env` ou de configuration contenant des credentials
- Vérifier avant chaque commit qu'aucun secret n'est présent

---

## Compatibilité multiplateforme

- Utiliser des fins de ligne LF (configurées dans `.gitattributes` et `.editorconfig`)
- Éviter les caractères spéciaux dans les noms de fichiers
- Les chemins référencés dans les exemples doivent être valides sur Linux, macOS et Windows

---

## Versionnement

- Chaque skill a sa propre version dans `metadata.yaml` (format `MAJOR.MINOR.PATCH`)
- Le dépôt global est versionné dans `CHANGELOG.md`
- Toute modification significative doit être documentée dans `CHANGELOG.md`
- Utiliser [Semantic Versioning](https://semver.org/lang/fr/) pour les skills et le dépôt

---

## Format des métadonnées

- Le champ `name` doit être en kebab-case
- Le champ `version` doit respecter SemVer (`1.0.0`, `0.2.1`)
- Le champ `status` doit être l'une des valeurs : `draft`, `experimental`, `stable`, `deprecated`
- Les tableaux (`tags`, `compatibility`, `authors`) ne doivent pas contenir de doublons
