# Permissions, jetons et branches protégées

Aucun secret ne va dans Git, dans `.gitmodules` ni dans une URL. Les jetons vivent dans les secrets
GitHub Actions ; le script les reçoit par l'environnement et ne les transmet à git que pour l'appel
qui en a besoin, sans rien écrire dans `.git/config`.

## Quel jeton pour quoi

| Besoin | Sans secret (`GITHUB_TOKEN`) | Secret à créer |
|--------|------------------------------|----------------|
| Lire un dépôt source **public** | suffit | aucun |
| Lire un dépôt source **privé** | impossible : sa portée est le dépôt du workflow | `SUBMODULE_FETCH_TOKEN` — « Contents: read » sur le dépôt source |
| Pousser la référence sur la branche destinataire | suffit, avec `contents: write` | aucun |
| Que ce push déclenche la CI du dépôt | impossible : un push fait avec `GITHUB_TOKEN` ne déclenche aucun workflow | `SUBMODULE_PUSH_TOKEN` — « Contents: read and write » sur ce dépôt |
| Mode `pr` avec contrôles obligatoires | les contrôles restent en attente d'approbation manuelle | `SUBMODULE_PUSH_TOKEN` — « Contents » et « Pull requests » en écriture |
| Être notifié par le producteur | sans objet | `SUBMODULE_DISPATCH_TOKEN`, **dans le dépôt producteur** |

Ces secrets acceptent un jeton personnel à permissions fines, limité aux dépôts cités, ou un jeton
d'installation de GitHub App, préférable : il n'est pas lié à une personne et sa durée est courte.

```bash
gh secret set SUBMODULE_FETCH_TOKEN --repo <propriétaire>/<consommateur>
```

La valeur se saisit à l'invite. Elle ne doit apparaître ni dans une commande ni dans un fichier.

Une installation en mode planifié ne demande **aucun droit d'écriture sur le dépôt source** : la
lecture suffit.

Préférer une URL `https://` dans `.gitmodules`. Une URL SSH est réécrite en HTTPS par le workflow
pour être authentifiée par jeton, mais reste ce que verront les autres outils.

## Ce que `GITHUB_TOKEN` ne fait pas

- Il n'a aucun droit hors du dépôt du workflow.
- Les événements qu'il provoque ne créent pas d'exécution de workflow, à deux exceptions près :
  `workflow_dispatch` et `repository_dispatch`. Un commit de mise à jour poussé avec lui ne lance
  donc pas la CI du dépôt.
- Une pull request qu'il ouvre voit ses workflows créés **en attente d'approbation** : quelqu'un
  doit cliquer. Pour une fusion sans intervention, la pull request doit être ouverte avec un jeton
  d'App ou un jeton personnel.

## Branche destinataire protégée

Le comportement nominal est un push direct. Si la branche l'interdit, **aucune protection n'est
désactivée ni contournée** : le push échoue (code 6) et le dit. Deux voies honnêtes.

### `mode=pr` : pull request à fusion automatique

```text
/install-git-submodule url=… branch=… target=… mode=pr
```

Le workflow pousse une branche `submodule-update/<branche>-<empreinte>`, ouvre une pull request,
active sa fusion automatique (`gh pr merge --auto --squash`), et ferme les pull requests de mise à
jour devenues obsolètes. Cela n'est entièrement automatique que si toutes ces conditions tiennent :

| Condition | Où |
|-----------|----|
| « Allow auto-merge » activé | réglages du dépôt |
| les contrôles obligatoires s'exécutent sur la pull request | donc ouverte avec `SUBMODULE_PUSH_TOKEN` et non `GITHUB_TOKEN` |
| aucune revue humaine obligatoire, ou une règle qui en dispense cet acteur | règles de la branche |
| si `GITHUB_TOKEN` est utilisé malgré tout : « Allow GitHub Actions to create and approve pull requests » | réglages Actions du dépôt |

Si une revue humaine est obligatoire pour tous, la mise à jour **ne peut pas** être entièrement
automatique : la pull request attendra une approbation. C'est un choix de gouvernance du dépôt, pas
un défaut à corriger par le skill.

### Autoriser l'acteur dans la règle

Le propriétaire du dépôt peut inscrire une GitHub App dans la liste de contournement de la règle et
fournir son jeton en `SUBMODULE_PUSH_TOKEN`. C'est une décision qui lui appartient ; le skill la
décrit, il ne la prend pas.

## Conditions de présence du workflow

- `repository_dispatch` et `schedule` ne déclenchent que les workflows présents sur la **branche par
  défaut**, et s'exécutent sur elle. Le workflow extrait ensuite la branche destinataire configurée,
  qui doit contenir `.github/submodule-update.json` et `.github/submodule-sync/`.
- Les exécutions planifiées peuvent être retardées aux heures de forte charge, voire abandonnées ;
  éviter la minute zéro. Dans un dépôt public, elles sont désactivées après soixante jours sans
  activité.

## Vérifier pour de bon

```bash
gh workflow run submodule-update.yml
```

```bash
gh run list --workflow submodule-update.yml --limit 5
```

Tant qu'aucune exécution verte n'a été observée, l'automatisation est installée, pas active.
