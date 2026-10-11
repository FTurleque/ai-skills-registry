# Exemple : installer `.claude` comme sous-module dans un dépôt qui en a déjà un

Exécution réelle du 11 octobre 2026, sous Windows 10 (git 2.51, Python 3.13), avec les scripts
lancés depuis l'installation globale `~/.claude/skills/install-git-submodule/`, dans un dépôt
temporaire hors du registre. Suite de
[publish-git-submodule/examples/publish-claude-folder.md](../../publish-git-submodule/examples/publish-claude-folder.md).
Les remotes sont des dépôts bare locaux ; les chemins temporaires sont abrégés en `<tmp>`.

## Le dépôt de départ

```text
application/        branche main
├── README.md
└── .claude/
    ├── CLAUDE.md               suivi, propre au projet — diffère de celui de la source
    └── settings.local.json     non suivi
```

## Demande

```text
/install-git-submodule url=<tmp>/toolkit.git branch=submodule/claude target=.claude auto=true
```

## 1. Simulation : une décision est nécessaire

```text
$ python ~/.claude/skills/install-git-submodule/resources/scripts/install.py apply url=<tmp>/toolkit.git branch=submodule/claude target=.claude dry-run=true
Contenu actuel de .claude comparé à la source :
  1 fichier(s) présents des deux côtés avec un contenu DIFFÉRENT — la version de la source s'installera, la vôtre ira dans la sauvegarde
    - CLAUDE.md
  1 fichier(s) non suivis ici et absents de la source — replacés tels quels, non suivis
    - settings.local.json
  1 fichier(s) apportés par la source
    - skills/demo/SKILL.md
ERREUR : .claude existe déjà et diffère de la source : rien n'a été modifié. Décision requise — relancer avec migrate=preserve pour appliquer exactement ce qui est décrit ci-dessus (sauvegarde intégrale, aucun fichier supprimé définitivement), ou déplacer d'abord ces fichiers.
```

Code de sortie 7. Le skill présente ce texte tel quel et pose une seule question : appliquer
`migrate=preserve`, ou déplacer d'abord `CLAUDE.md` ?

## 2. Installation, après accord

```text
$ python …/install.py apply url=<tmp>/toolkit.git branch=submodule/claude target=.claude migrate=preserve commit=true push=true
.claude : migrated (<tmp>/toolkit.git@submodule/claude, tête 104e415fee43)
Sauvegarde intégrale de l'ancien dossier : <tmp>/application/.git/submodule-sync-backups/claude-20261011T002131Z
Fichiers locaux replacés non suivis : 1
ATTENTION : URL locale : utilisable sur ce poste, pas par GitHub Actions
Fichiers gérés : .gitmodules, .claude, .github/submodule-update.json, .github/workflows/submodule-update.yml, .github/submodule-sync/UPDATE.md, .github/submodule-sync/update.py, .github/submodule-sync/submodule_common.py
Clonage : git clone --recurse-submodules <url>   (clone existant : git submodule update --init)
Mise à jour sur événement : dans le dépôt source, inscrire ce dépôt — /publish-git-submodule register name=<publication> consumer=<propriétaire>/<dépôt>
```

```text
$ ls -A .claude
.git  CLAUDE.md  settings.local.json  skills
```

`.claude/CLAUDE.md` est désormais celui de la source ; l'ancien est dans la sauvegarde ;
`settings.local.json` est resté en place, non suivi. Pas de `.claude/.claude/`.

## 3. Adoption d'une nouvelle version

Le producteur a publié `cba3c73b5dd8`. C'est ce que lance le workflow :

```text
$ python .github/submodule-sync/update.py run --push
.claude : updated (104e415fee43 -> cba3c73b5dd8)
Poussé : main

$ git log -1 --format=%B
chore(submodule): .claude -> cba3c73b5dd8

Submodule-Path: .claude
Submodule-Url: <tmp>/toolkit.git
Submodule-Branch: submodule/claude
Submodule-Old: 104e415fee436a0e302305102221f5187647551e
Submodule-New: cba3c73b5dd88500b39213b68963389cfcadc528
```

## 4. Relance sans changement

```text
$ python .github/submodule-sync/update.py run --push
.claude : unchanged

$ python .github/submodule-sync/update.py status
.claude : <tmp>/toolkit.git@submodule/claude — enregistré cba3c73b5dd8, branche cba3c73b5dd8 — à jour
```

## Pourquoi c'est le bon résultat

- La simulation n'a rien modifié et a nommé chaque fichier concerné : la décision porte sur des
  faits, pas sur un résumé.
- Aucun fichier n'a disparu : la version du projet de `CLAUDE.md` est dans la sauvegarde, le fichier
  local est toujours là, et rien n'a été envoyé vers la source partagée.
- Le commit de mise à jour ne contient que la référence du sous-module ; la relance n'en crée pas.
- Ce que cet exemple ne montre pas : l'exécution du workflow sur GitHub, ses permissions et ses
  secrets. L'URL locale de cet essai ne serait d'ailleurs pas utilisable par GitHub Actions, ce que
  le script signale.
