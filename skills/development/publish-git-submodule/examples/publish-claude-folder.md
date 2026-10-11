# Exemple : publier le dossier `.claude` d'un dépôt

Exécution réelle du 11 octobre 2026, sous Windows 10 (git 2.51, Python 3.13), avec les scripts
lancés depuis l'installation globale `~/.claude/skills/publish-git-submodule/`, dans un dépôt
temporaire hors du registre. Le remote est un dépôt bare local : cela exerce toute la logique git,
pas GitHub Actions. Les chemins temporaires sont abrégés en `<tmp>`.

## Le dépôt de départ

```text
toolkit/            branche main, remote origin = <tmp>/toolkit.git
├── app/main.py
└── .claude/
    ├── CLAUDE.md
    └── skills/demo/SKILL.md
```

## Demande

```text
/publish-git-submodule source=.claude branch=main export=submodule/claude auto=true
```

## 1. Simulation

```text
$ python ~/.claude/skills/publish-git-submodule/resources/scripts/publish.py setup source=.claude branch=main export=submodule/claude auto=true dry-run=true
claude : .claude -> submodule/claude @ 104e415fee43 [serait créée] (source 37aa33a687b1)
Installation chez un consommateur : /install-git-submodule url=<tmp>/toolkit.git branch=submodule/claude target=.claude auto=true
```

Rien n'est écrit. Aucun constat de contenu sensible : la publication peut avoir lieu.

## 2. Publication

```text
$ python …/publish.py setup source=.claude branch=main export=submodule/claude auto=true commit=true push=true
claude : .claude -> submodule/claude @ 104e415fee43 [branche créée] (source 37aa33a687b1)
Fichiers gérés : .github/submodule-publish.json, .github/submodule-sync/PUBLISH.md, .github/submodule-sync/publish.py, .github/submodule-sync/submodule_common.py, .github/workflows/submodule-publish.yml
Installation chez un consommateur : /install-git-submodule url=<tmp>/toolkit.git branch=submodule/claude target=.claude auto=true
```

La branche d'export porte le contenu du dossier **à sa racine**, sans le code de l'application :

```text
$ git ls-tree -r --name-only origin/submodule/claude
CLAUDE.md
skills/demo/SKILL.md
```

## 3. Relance sans changement

```text
$ python .github/submodule-sync/publish.py run --all --push
claude : .claude -> submodule/claude @ 104e415fee43 [inchangé] (source e36e2ef475ba)
```

Le commit source a changé (c'est le commit de configuration), l'export non : aucun push, aucune
notification.

## 4. Nouvelle version

Après modification de `.claude/CLAUDE.md` et push sur `main` — c'est ce que lance le workflow :

```text
$ python .github/submodule-sync/publish.py run --all --push
claude : .claude -> submodule/claude @ cba3c73b5dd8 [mis à jour] (source d06fd331c122)
```

## Pourquoi c'est le bon résultat

- `104e415fee43` est identique en simulation et en publication : l'extraction est déterministe,
  d'où la relance sans effet.
- La branche `main` n'a reçu que le commit des fichiers gérés ; l'extraction ne l'a pas touchée.
- Ce que cet exemple ne montre pas : l'exécution du workflow sur GitHub. Elle reste à constater sur
  un vrai dépôt, avec `gh run list --workflow submodule-publish.yml`.

La suite, côté consommateur :
[install-git-submodule/examples/install-claude-submodule.md](../../install-git-submodule/examples/install-claude-submodule.md).
