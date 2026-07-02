# Processus de contribution

Ce document décrit en détail comment créer et soumettre un nouveau skill dans le dépôt **AI Skills Registry**.

---

## Étapes recommandées

### 1. Copier le template

Copier le dossier `templates/skill-template/` dans la catégorie adaptée :

```bash
cp -r templates/skill-template/ skills/shared/development/mon-skill/
```

Renommer le dossier avec un nom en kebab-case représentant clairement le skill.

### 2. Choisir une catégorie

Placer le skill dans la catégorie la plus adaptée :

| Catégorie       | Exemples de skills                    |
|-----------------|---------------------------------------|
| `development/`  | revue de code, génération de code     |
| `documentation/`| rédaction de README, commentaires     |
| `refactoring/`  | extraction de méthodes, simplification|
| `testing/`      | génération de tests, analyse de couverture |
| `analysis/`     | audit de dépendances, analyse de logs |

Si aucune catégorie n'est adaptée, créer une nouvelle catégorie dans `skills/shared/` et la documenter dans `docs/architecture.md`.

### 3. Renseigner les métadonnées

Remplir le front matter YAML de `SKILL.md` :

```yaml
---
name: mon-skill
displayName: Mon Skill
description: Description courte et précise du skill.
version: 1.0.0
status: draft
category: development
tags:
  - exemple
  - tag
compatibility:
  - generic
authors:
  - Votre Nom
license: MIT
---
```

Remplir également `metadata.yaml` avec les mêmes informations.

### 4. Rédiger les instructions

Dans `SKILL.md`, rédiger le corps du skill avec les sections appropriées :

- **Objectif** — ce que fait le skill
- **Cas d'utilisation** — quand l'utiliser
- **Entrées attendues** — ce que l'utilisateur doit fournir
- **Instructions** — les étapes détaillées pour l'assistant IA
- **Contraintes** — les limites et règles à respecter
- **Processus d'exécution** — l'ordre des opérations
- **Format de sortie** — la structure de la réponse attendue
- **Critères de validation** — comment vérifier que le résultat est correct
- **Exemples** — références vers `examples/`
- **Limites** — ce que le skill ne peut pas faire

### 5. Ajouter des exemples

Créer au moins un fichier dans `examples/` décrivant un cas d'usage concret :

- Fournir une entrée représentative
- Montrer la sortie attendue
- Illustrer les cas limites si pertinent

### 6. Valider la compatibilité

- Tester le skill avec les outils déclarés dans `compatibility`
- Mettre à jour la matrice dans `docs/compatibility.md`
- Documenter les éventuelles limitations dans le `README.md` du skill

### 7. Mettre à jour le changelog

Ajouter une entrée dans `CHANGELOG.md` :

```markdown
## [Non publié]

### Ajouté
- Nouveau skill : `mon-skill` — description courte
```

### 8. Créer une pull request

- Pousser les modifications sur une branche dédiée
- Créer une pull request en utilisant le modèle disponible
- Compléter la checklist fournie dans le modèle
- Demander une revue si nécessaire

---

## Modifier un skill existant

1. Modifier les fichiers concernés
2. Incrémenter la version dans `SKILL.md` et `metadata.yaml`
3. Mettre à jour `CHANGELOG.md`
4. Créer une pull request

---

## Conventions à respecter

Voir [conventions.md](conventions.md) pour l'ensemble des règles de nommage, de documentation et de sécurité.
