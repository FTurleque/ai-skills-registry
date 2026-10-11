# Publier une source de sous-module Git

> Prépare un dépôt, ou un seul de ses dossiers, pour être installé comme sous-module ailleurs, et automatise sa republication.

## Ce que ça change

Partager un dossier `.claude/`, une documentation ou une bibliothèque entre plusieurs dépôts finit
souvent en copies qui divergent. Avec ce skill :

- un **dépôt entier** est vérifié et enregistré comme source, sans branche d'export inutile ;
- un **dossier** est extrait à la racine d'une branche d'export du même dépôt (`git subtree split`),
  de sorte qu'installé dans `.claude/` il ne produit jamais `.claude/.claude/` ;
- avant tout push, le contenu **et son historique** sont contrôlés : réglages locaux, secrets,
  chemins personnels ;
- un workflow GitHub Actions republie après chaque push qui touche le dossier, sans `push --force`
  ni commit inutile, puis notifie les dépôts consommateurs inscrits ;
- les synchronisations ordinaires tournent en scripts : aucun appel à Claude, aucun crédit consommé.

L'autre moitié, côté dépôt destinataire, est le skill
[`install-git-submodule`](../install-git-submodule/README.md). Vue d'ensemble des deux :
[docs/git-submodule-sync.md](../../../docs/git-submodule-sync.md).

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/publish-git-submodule/` | scripts exercés depuis cet emplacement (Windows 10) ; invocation `/publish-git-submodule` non exercée |
| Claude Code, portée projet | `<projet>/.claude/skills/publish-git-submodule/` | non vérifié |

```bash
python tools/install_skill.py install publish-git-submodule install-git-submodule
```

```bash
python tools/install_skill.py check publish-git-submodule install-git-submodule
```

L'installateur copie le dossier entier, sauvegarde une installation antérieure modifiée, et `check`
dit si la copie globale correspond au dépôt. Voir [docs/install.md](../../../docs/install.md).

Prérequis : `git` avec `git subtree`, Python 3.8+. `gh` est utile pour poser le secret et lire les
exécutions, pas obligatoire.

## Usage

```text
/publish-git-submodule source=. branch=main auto=true
/publish-git-submodule source=.claude branch=main export=submodule/claude auto=true
/publish-git-submodule source=docs branch=main export=submodule/docs auto=true
/publish-git-submodule source=.claude strategy=snapshot exclude=*.local.json
/publish-git-submodule register name=claude consumer=acme/application
/publish-git-submodule status
```

Cette syntaxe est celle des arguments du skill, pas une commande Git. Le skill ne se déclenche
jamais seul (`disable-model-invocation: true`) : il publie.

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `source` | `.` | `.` pour le dépôt entier, sinon un dossier |
| `branch` | branche par défaut du remote, détectée | branche source |
| `export` | `submodule/<dossier>` | branche d'export, mode dossier |
| `auto` | `true` | installer le workflow |
| `strategy` | `subtree` | `snapshot` : export sans historique, accepte `exclude` |
| `consumer` | — | dépôt à notifier |
| `push` | demander | pousser le commit de configuration |

Le skill simule d'abord, publie ensuite, et termine par la commande exacte à lancer chez le
consommateur. Fichiers créés dans le dépôt : `.github/submodule-publish.json`,
`.github/submodule-sync/` (scripts et notice), `.github/workflows/submodule-publish.yml`.

Exemple réel : [examples/publish-claude-folder.md](examples/publish-claude-folder.md).

## Détails

| Sujet | Fichier |
|-------|---------|
| Les deux modes, le flux, plusieurs publications | [resources/references/architecture.md](resources/references/architecture.md) |
| Contenu sensible, historique, `snapshot`, branche réécrite | [resources/references/security-and-history.md](resources/references/security-and-history.md) |
| Workflow, `GITHUB_TOKEN`, notification, secret | [resources/references/automation.md](resources/references/automation.md) |
| Diagnostic, reprise, désactivation | [resources/references/troubleshooting.md](resources/references/troubleshooting.md) |

## Tests

```bash
python -m unittest discover -s skills/development/publish-git-submodule/tests
```

Vingt et un tests sur des dépôts temporaires et des remotes bare locaux : export à la racine, relance
sans commit, avance rapide, dépôt entier, plusieurs publications, chemin avec espaces, contenu
sensible, `snapshot`, historique réécrit, notification vers un serveur HTTP local, YAML généré.

## Limites

- **Le fonctionnement sur GitHub n'a pas été observé.** Les workflows générés sont des gabarits
  validés statiquement ; permissions, secrets et déclencheurs réels restent à vérifier sur un vrai
  dépôt (`gh run list`). Le skill ne déclare jamais l'automatisation active.
- **Extraire un dossier n'isole ni les objets Git ni les droits** : la branche d'export vit dans le
  même dépôt. Pour cloisonner des accès, il faut un dépôt distinct.
- **`subtree` publie l'historique du dossier.** Un fichier retiré y reste. D'où le contrôle de
  l'historique et la stratégie `snapshot`.
- **Le contrôle de contenu ne connaît que des formats reconnaissables** et saute binaires et gros
  fichiers.
- **Un dossier qui contient un sous-module n'est pas publiable** : son `.gitmodules` resterait à la
  racine de la source.
- **Notifier un autre dépôt exige un jeton « Contents: write »** sur ce dépôt : c'est l'exigence de
  l'API, plus large que le besoin.
- **GitHub seulement** pour l'automatisation. L'extraction et la publication initiale fonctionnent
  avec n'importe quel remote Git.
- Caractères refusés dans les chemins et les branches : `* ? [ ] { } " ' $ \ < > | ; &` et l'accent
  grave. Les espaces sont acceptés dans les chemins.
- **Surface `claude-code` seule.** Le front matter porte des champs propres au registre, tolérés par
  Claude Code.
