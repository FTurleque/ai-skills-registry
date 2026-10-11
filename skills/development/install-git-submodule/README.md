# Installer un sous-module Git mis à jour automatiquement

> Installe un sous-module qui suit une branche d'un autre dépôt, et la mécanique qui le tient à jour sans intervention.

## Ce que ça change

Un sous-module ajouté à la main reste figé sur le commit du jour, et un dossier cible déjà rempli
finit souvent écrasé. Avec ce skill :

- le sous-module est ajouté avec sa **branche suivie** explicitement inscrite dans `.gitmodules` ;
- un **dossier cible déjà présent** n'est jamais supprimé ni écrasé directement : il est comparé à
  la source fichier par fichier, sauvegardé en entier, et toute divergence demande une décision ;
- un workflow GitHub Actions avance la référence sur **événement** du producteur, sur
  **planification** et à la main, lance les contrôles du dépôt, puis pousse un commit qui ne
  contient que cette référence ;
- rien n'est commité quand rien n'a changé ; un événement ancien ou en double ne fait ni reculer ni
  doublonner ; un travail local dans le sous-module n'est jamais écrasé ;
- les synchronisations ordinaires tournent en scripts : aucun appel à Claude, aucun crédit consommé.

L'autre moitié, côté dépôt source, est le skill
[`publish-git-submodule`](../publish-git-submodule/README.md). Vue d'ensemble des deux :
[docs/git-submodule-sync.md](../../../docs/git-submodule-sync.md).

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/install-git-submodule/` | scripts exercés depuis cet emplacement (Windows 10) ; invocation `/install-git-submodule` non exercée |
| Claude Code, portée projet | `<projet>/.claude/skills/install-git-submodule/` | non vérifié |

```bash
python tools/install_skill.py install publish-git-submodule install-git-submodule
```

```bash
python tools/install_skill.py check publish-git-submodule install-git-submodule
```

Les deux skills sont indépendants à l'usage ; les installer ensemble garde identique le module
qu'ils partagent. Voir [docs/install.md](../../../docs/install.md).

Prérequis : `git` 2.38+, Python 3.8+. `gh` sert à lire la protection de branche et les exécutions ;
il n'est obligatoire que pour le mode `pr`, où le workflow l'utilise (il est préinstallé sur les
runners GitHub).

## Usage

```text
/install-git-submodule url=https://github.com/acme/toolkit.git branch=submodule/claude target=.claude auto=true
/install-git-submodule url=https://github.com/acme/outil.git branch=main target=vendor/outil auto=true
/install-git-submodule url=… branch=submodule/docs target=docs/shared schedule="41 3 * * *" check="python tools/validate.py"
/install-git-submodule url=… branch=… target=… mode=pr
/install-git-submodule status
```

Cette syntaxe est celle des arguments du skill, pas une commande Git. Le skill ne se déclenche
jamais seul (`disable-model-invocation: true`).

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `url`, `branch`, `target` | obligatoires | dépôt source, branche à suivre, dossier d'installation |
| `auto` | `true` | installer la mise à jour automatique |
| `schedule` | `17 */6 * * *` | cron UTC du rattrapage ; `none` pour le retirer |
| `target-branch` | branche par défaut, détectée | branche qui reçoit les mises à jour |
| `mode` | `push` | `pr` pour une branche protégée |
| `check` | — | commande de contrôle avant tout commit |
| `migrate` | — | `preserve` : migrer un dossier existant qui diffère |
| `push` | demander | pousser le commit d'installation |

Fichiers créés dans le dépôt : `.gitmodules` et la référence du sous-module,
`.github/submodule-update.json`, `.github/submodule-sync/` (scripts et notice de clonage),
`.github/workflows/submodule-update.yml`. Plusieurs sous-modules se partagent ces fichiers.

Exemple réel : [examples/install-claude-submodule.md](examples/install-claude-submodule.md).

## Détails

| Sujet | Fichier |
|-------|---------|
| Dossier cible existant, sous-module déjà présent | [resources/references/migration.md](resources/references/migration.md) |
| Jetons, dépôts privés, branche protégée, mode `pr` | [resources/references/permissions.md](resources/references/permissions.md) |
| Événement, planification, garde-fous, postes de travail | [resources/references/automation.md](resources/references/automation.md) |
| Diagnostic, retour à un ancien commit, désactivation | [resources/references/troubleshooting.md](resources/references/troubleshooting.md) |

## Tests

```bash
python -m unittest discover -s skills/development/install-git-submodule/tests
```

Vingt et un tests de bout en bout sur des dépôts temporaires et des remotes bare locaux, avec le skill
voisin : installation, adoption d'une nouvelle version, dépôt entier, plusieurs sous-modules, chemin
avec espaces, dossier existant identique puis divergent, travail local, contrôle en échec,
événements en double, anciens, étrangers et mal formés, branche réécrite, push rejeté, mode `pr`
avec un `gh` simulé, YAML généré.

## Limites

- **Le fonctionnement sur GitHub n'a pas été observé.** Le workflow généré est un gabarit validé
  statiquement ; l'authentification par jeton, les secrets, les déclencheurs et les protections de
  branche réels restent à vérifier sur un vrai dépôt. Le skill ne déclare jamais l'automatisation
  active.
- **Le mode `pr` n'a été exercé qu'avec un `gh` simulé** : la séquence de commandes est vérifiée,
  pas la fusion automatique elle-même. Avec une revue humaine obligatoire, la mise à jour ne peut
  pas être entièrement automatique.
- **Un sous-module occupe tout son dossier.** Un fichier propre au projet n'y est plus versionné
  par le dépôt consommateur : il y reste non suivi, ou doit être déplacé.
- **Le dépôt distant est mis à jour, pas les clones** : `git submodule update --init` reste à faire
  sur chaque poste, ou `git config submodule.recurse true`.
- **Un push fait avec `GITHUB_TOKEN` ne déclenche pas la CI du dépôt** ; il faut un autre jeton pour
  cela.
- **Un dépôt source privé exige un secret de lecture**, et qui lit la branche d'export lit tout le
  dépôt source.
- **Les contrôles passent par le shell du système** : `sh` sur un runner, `cmd` sur un poste Windows.
- **GitHub seulement** pour l'automatisation. L'installation et la mise à jour manuelle fonctionnent
  avec n'importe quel remote Git.
- Caractères refusés dans les chemins et les branches : `* ? [ ] { } " ' $ \ < > | ; &` et l'accent
  grave. Les espaces sont acceptés dans les chemins.
- **Surface `claude-code` seule.** Le front matter porte des champs propres au registre, tolérés par
  Claude Code.
