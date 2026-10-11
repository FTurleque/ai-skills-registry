# Publication automatique et notification

## Ce que fait le workflow

`.github/workflows/submodule-publish.yml`, généré à partir de `.github/submodule-publish.json` :

| Déclencheur | Effet |
|-------------|-------|
| `push` sur une branche source, filtré sur les dossiers publiés, la configuration et les scripts | republie les exports de cette branche |
| `workflow_dispatch` | republie tout ; l'option `notify` renvoie la notification même sans changement |

Il récupère tout l'historique (`fetch-depth: 0`), extrait, compare à la branche d'export, et ne
pousse que si le résultat diffère. Pas de `push --force` par défaut, pas de commit ni de
notification quand rien n'a changé. Les exécutions d'une même branche se suivent sans s'annuler,
et chacune publie le dernier commit de la branche, pas celui de son événement. Aucun modèle d'IA
n'est appelé : git, Python (préinstallé sur les runners) et l'API GitHub.

Dès qu'une publication porte sur le dépôt entier, le filtre de chemins disparaît : tout push de la
branche est une nouvelle version.

## `GITHUB_TOKEN` : portée et limites

- Sa portée est le dépôt du workflow. Il pousse la branche d'export (`contents: write`), il ne peut
  rien dans un autre dépôt.
- Un push fait avec lui **ne déclenche aucun autre workflow** `push`. C'est pourquoi publication
  et notification se font dans la même exécution, et non dans un second workflow déclenché par la
  branche d'export.
- Seules exceptions documentées par GitHub : `workflow_dispatch` et `repository_dispatch` créent
  toujours une exécution — mais envoyer un `repository_dispatch` à un **autre** dépôt demande un
  autre jeton.

## Notifier les consommateurs

Un consommateur s'inscrit auprès du producteur :

```text
/publish-git-submodule register name=claude consumer=acme/application
```

La liste vit dans la configuration (`consumers`). Elle peut rester vide : la première publication
n'a besoin d'aucun consommateur, et un consommateur en mode planifié n'a pas besoin d'être inscrit.

Après une publication qui change l'export, le script envoie à chaque inscrit un événement
`repository_dispatch` de type `submodule-updated`, avec `source_repo`, `branch`, `sha`, `source_sha`
et `publication`. Le consommateur revalide tout et n'adopte que la tête réelle de la branche.

Cela exige un secret dans le dépôt producteur :

| Secret | Contenu | Permission minimale |
|--------|---------|---------------------|
| `SUBMODULE_DISPATCH_TOKEN` | jeton à permissions fines, ou jeton d'installation d'une GitHub App | « Contents: read and write » sur les **seuls dépôts consommateurs** |

C'est la permission que l'API GitHub exige pour créer un `repository_dispatch` ; elle est plus large
que le besoin, d'où l'intérêt de restreindre le jeton aux dépôts concernés. Une GitHub App évite un
jeton lié à une personne et délivre des jetons à durée courte. Créer le secret :

```bash
gh secret set SUBMODULE_DISPATCH_TOKEN --repo <propriétaire>/<producteur>
```

La valeur se saisit à l'invite : elle ne doit apparaître ni dans une commande, ni dans un fichier,
ni dans une URL.

Sans ce secret, la publication réussit et le workflow émet un avertissement ; les consommateurs se
mettent à jour à leur prochaine exécution planifiée. Avec un secret invalide, la publication réussit
et l'exécution échoue sur la notification, pour que le défaut soit visible.

## Conditions de présence

- Le workflow agit sur un `push` quand il est présent sur la branche poussée.
- Le lancement manuel exige sa présence sur la branche par défaut.
- Tant que le commit de configuration n'est pas sur la branche source, seule la publication initiale
  (faite par le skill) existe.

## Vérifier pour de bon

Les tests locaux prouvent la logique, pas les permissions. Après le premier push :

```bash
gh run list --workflow submodule-publish.yml --limit 5
```

```bash
gh run view <id> --log-failed
```
