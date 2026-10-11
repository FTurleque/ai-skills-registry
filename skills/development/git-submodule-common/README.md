# Sous-modules Git — module partagé

> Le code commun aux skills `publish-git-submodule` et `install-git-submodule`, en un seul exemplaire.

## Ce que c'est

Un module Python, `resources/scripts/submodule_common.py`, importé par les scripts des deux skills.
Ce n'est pas un skill qu'on invoque : il ne se déclenche pas et n'apparaît pas dans le menu `/`.

## Ce que ça change

Les deux skills partagent la même façon de lancer git (sans shell), de valider un chemin, une
branche ou une URL, de transmettre un jeton à git sans rien écrire dans `.git/config`, et d'écrire
les fichiers qu'ils gèrent. Ce code n'existe qu'ici : une correction vaut pour les deux, et ils ne
peuvent pas diverger.

## Installation

Toujours avec les deux skills, dans le même dossier :

```bash
python tools/install_skill.py install git-submodule-common publish-git-submodule install-git-submodule
```

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/git-submodule-common/` | oui (Windows 10) : scripts des deux skills lancés depuis `~/.claude/skills/` |
| Claude Code, portée projet | `<projet>/.claude/skills/git-submodule-common/` | non vérifié |

Voir [docs/git-submodule-sync.md](../../../docs/git-submodule-sync.md) pour l'usage des deux skills.

Exemple : [examples/shared-module.md](examples/shared-module.md).

## Limites

- **Inutile seul**, et **indispensable aux deux autres** : sans ce dossier à côté d'eux, leurs
  scripts s'arrêtent avec un message qui le dit.
- Dans un dépôt producteur ou consommateur, les scripts sont copiés avec ce module dans
  `.github/submodule-sync/`. Cette copie-là ne se met pas à jour seule : relancer le skill concerné
  la rafraîchit.
- **Surface `claude-code` seule.** Le front matter porte des champs propres au registre, tolérés par
  Claude Code.
