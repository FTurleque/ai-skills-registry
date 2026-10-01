# Conventions du dépôt

Règles à respecter pour maintenir la cohérence de **AI Toolkit Registry**. Celles qui sont
vérifiables automatiquement le sont par `python tools/validate.py` ; la colonne le précise.

---

## Langue

| Règle | Vérifié |
|-------|---------|
| Noms de dossiers et de fichiers en **anglais** | non |
| Documentation (README, SKILL.md, exemples) en **français** | non |
| Champs de métadonnées en **anglais**, valeurs en anglais sauf `description` et `displayName` | non |

---

## Nommage

| Règle | Vérifié |
|-------|---------|
| Nom d'artefact en **kebab-case** : `java-code-review` | oui |
| Le champ `name` est égal au nom du dossier, ou du fichier sans extension | oui |
| Le champ `category` d'une skill est égal au nom de son dossier parent | oui |
| Le champ `kind` correspond au dossier de premier niveau | oui |
| Deux artefacts n'ont jamais le même nom, même de types différents | oui |
| Les fichiers standards gardent leur nom exact : `SKILL.md`, `metadata.yaml`, `README.md`, `plugin.json`, `hooks.json` | oui |

Un nom d'artefact décrit ce qu'il fait, à la façon d'un nom de méthode : `generate-windows-exe` et
non `windows-helper`, `java-code-review` et non `review-tool`.

---

## Identifiants stables

Un artefact publié ne se renomme pas sans raison. Quand c'est nécessaire :

1. Renommer le dossier ou le fichier **et** le champ `name`.
2. Lister l'ancien identifiant ou l'ancien chemin dans le champ `replaces`.
3. Documenter le changement dans `CHANGELOG.md`.
4. Incrémenter la version **majeure** si le renommage casse une installation existante — c'est le
   cas d'un plugin, dont le nom est le suffixe d'installation.

---

## Documentation

| Règle | Vérifié |
|-------|---------|
| Chaque artefact a un `README.md` compréhensible sans lire le reste | oui (présence) |
| Chaque artefact en dossier a au moins un exemple dans `examples/` | non |
| Le `README.md` dit **comment installer** l'artefact, pas seulement ce qu'il fait | non |
| Les instructions sont explicites et vérifiables : entrées, sorties, critères de validation | non |

Le `README.md` d'un artefact répond à quatre questions, dans cet ordre : qu'est-ce que c'est, ce que
ça change concrètement, comment on l'installe, où sont ses limites. Les limites ne sont pas
facultatives : un artefact dont on ne connaît pas les angles morts est un piège.

---

## Métadonnées

| Règle | Vérifié |
|-------|---------|
| `version` respecte SemVer | oui |
| `status` vaut `draft`, `experimental`, `stable` ou `deprecated` | oui |
| `compatibility` ne contient que des surfaces connues | oui |
| Les tableaux ne contiennent pas de doublon | oui |
| Un `SKILL.md` et son `metadata.yaml` portent exactement les mêmes valeurs | oui |
| Aucun champ inconnu : le schéma est fermé | oui |

Le statut est une promesse faite au lecteur. `stable` veut dire que l'artefact a été utilisé pour de
vrai et que ses limites sont documentées ; `experimental` qu'il fonctionne mais que son
comportement peut changer ; `draft` qu'il n'est pas prêt à être utilisé.

---

## Aucun chemin absolu local

| Règle | Vérifié |
|-------|---------|
| Pas de `C:\Users\...`, `/home/<nom>/`, `/Users/<nom>/`, ni de chemin de poste de travail | oui |

Utiliser des chemins relatifs, ou les variables conventionnelles : `<project-root>`, `~/.claude/`,
`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`. Un chemin absolu dans un artefact est une erreur de
validation, pas un avertissement : il rend l'artefact inutilisable pour quelqu'un d'autre.

---

## Aucun secret

| Règle | Vérifié |
|-------|---------|
| Pas de jeton, clé d'API, mot de passe, clé privée ni donnée personnelle | oui (motifs connus) |
| Pas de `.env` ni de fichier de configuration contenant des identifiants | oui (`.gitignore`) |
| Les configurations MCP lisent leurs secrets depuis l'environnement | non |

La détection couvre les formats reconnaissables : clés AWS, jetons GitHub et Slack, JWT, clés
privées. Elle ne remplace pas une relecture : un mot de passe quelconque dans une chaîne de
connexion passe les motifs.

---

## Compatibilité multiplateforme

| Règle | Vérifié |
|-------|---------|
| Fins de ligne LF | oui (avertissement) |
| Pas de caractère spécial dans les noms de fichiers | non |
| Les chemins des exemples sont valides sous Linux, macOS et Windows | non |
| Un script livré précise son interpréteur et ses prérequis dans `requires` | non |

Un artefact qui ne fonctionne que sur une plateforme le dit dans son `README.md` et dans
`requires` — ce n'est pas un défaut, c'est une information.

---

## Versionnement

| Règle | Vérifié |
|-------|---------|
| Chaque artefact porte sa version dans ses métadonnées | oui |
| Le dépôt est versionné dans `CHANGELOG.md`, au format Keep a Changelog | non |
| Toute modification d'un artefact publié incrémente sa version | non |

Correction sans changement de comportement : `PATCH`. Ajout rétrocompatible : `MINOR`. Changement
qui casse un usage existant, renommage inclus : `MAJOR`.

---

## Index et catalogue

| Règle | Vérifié |
|-------|---------|
| `INDEX.md` est à jour | oui |
| `INDEX.md` n'est jamais édité à la main | non |
| Chaque artefact figure dans la matrice de `docs/surfaces.md` | oui (avertissement) |

---

## Ce que le dépôt ne contient pas

- Aucun artefact qui neutralise un contrôle de qualité ou de sécurité pour faire taire un
  avertissement.
- Aucun style de sortie ni jeu d'instructions qui demande à Claude de valider sans réserve, de
  taire un désaccord ou de cesser de vérifier. Un artefact décrit **comment** travailler, jamais
  **quoi** conclure.
- Aucun code dont l'effet n'est pas documenté dans son `README.md`. Pour un hook, qui s'exécute
  sans être appelé, c'est une condition d'entrée.
