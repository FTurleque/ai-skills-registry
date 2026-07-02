## Description

Décrire brièvement les modifications apportées par cette pull request.

## Type de changement

- [ ] Nouveau skill
- [ ] Modification d'un skill existant
- [ ] Correction de documentation
- [ ] Modification de configuration
- [ ] Autre : ___

## Skill(s) concerné(s)

Indiquer le ou les skills créés ou modifiés :

- `skills/…/nom-du-skill/`

## Checklist de validation

### Nommage

- [ ] Le nom du skill est en kebab-case
- [ ] Le nom du dossier correspond au champ `name` dans les métadonnées
- [ ] Les noms de fichiers respectent les conventions du dépôt

### Métadonnées

- [ ] Le front matter YAML de `SKILL.md` est complet et valide
- [ ] `metadata.yaml` est renseigné et cohérent avec `SKILL.md`
- [ ] Le champ `version` respecte le Semantic Versioning
- [ ] Le champ `status` est l'une des valeurs autorisées (`draft`, `experimental`, `stable`, `deprecated`)
- [ ] Les tableaux `tags`, `compatibility` et `authors` ne contiennent pas de doublons

### Documentation

- [ ] `SKILL.md` contient les sections principales
- [ ] `README.md` est lisible et compréhensible sans lire `SKILL.md`
- [ ] Les instructions sont claires, explicites et testables
- [ ] Aucun chemin local spécifique à un poste n'est mentionné

### Exemples

- [ ] Au moins un exemple est présent dans `examples/`
- [ ] Les exemples illustrent des cas d'usage réels ou représentatifs
- [ ] Les exemples respectent les conventions du dépôt

### Compatibilité

- [ ] Le champ `compatibility` est renseigné
- [ ] La compatibilité a été testée ou documentée pour chaque outil déclaré
- [ ] La matrice dans `docs/compatibility.md` est mise à jour si nécessaire

### Sécurité

- [ ] Aucun secret, token, clé API ou donnée personnelle sensible n'est inclus
- [ ] Aucun chemin absolu local n'est présent

### Versionnement

- [ ] `CHANGELOG.md` a été mis à jour
- [ ] La version du skill a été incrémentée si un skill existant a été modifié

## Notes pour les reviewers

Ajouter toute information utile pour faciliter la revue.
