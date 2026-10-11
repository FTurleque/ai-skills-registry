# Exemple : où vit le module, et ce qui se passe sans lui

Relevé le 11 octobre 2026 sous Windows 10, après installation des trois dossiers.

## Installé à côté des deux skills

```text
~/.claude/skills/
├── git-submodule-common/resources/scripts/submodule_common.py
├── publish-git-submodule/resources/scripts/publish.py
└── install-git-submodule/resources/scripts/install.py, update.py
```

`publish.py` et `update.py` cherchent `submodule_common.py` d'abord à côté d'eux, puis dans
`../../../git-submodule-common/resources/scripts/`.

## Copié dans un dépôt

Après `/install-git-submodule …` dans un dépôt consommateur :

```text
.github/submodule-sync/
├── UPDATE.md
├── submodule_common.py     copie du module partagé
└── update.py
```

Le workflow lance `python3 .github/submodule-sync/update.py` : le module est trouvé à côté du
script, aucun skill n'a besoin d'être installé sur le runner. Un test le vérifie
(`test_scripts_compile_and_installed_copies_run_on_their_own`).

## Sans le module

Si `git-submodule-common` n'est pas installé à côté des skills, le script s'arrête avant toute
action :

```text
module commun introuvable : installer `git-submodule-common` à côté de ce skill (python tools/install_skill.py install git-submodule-common)
```

C'est le bon résultat : un arrêt immédiat et explicite, plutôt qu'une publication à moitié faite.
