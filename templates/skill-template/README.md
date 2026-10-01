# Nom du Skill

Une phrase qui dit ce que le skill apporte.

## Ce que ça change

Décrire concrètement la différence entre avec et sans. Un exemple vaut mieux qu'une promesse.

## Installation

| Surface | Emplacement |
|---------|-------------|
| Claude Code | `~/.claude/skills/<nom>/` ou `<projet>/.claude/skills/<nom>/` |
| Application de bureau | réglages de l'application, ou via un plugin |
| claude.ai | téléverser le dossier dans les skills du compte ou du projet |

```bash
cp -r skills/<catégorie>/<nom> ~/.claude/skills/
```

Voir [docs/install.md](../../../docs/install.md) pour le détail par surface.

## Usage

Comment on s'en sert, et ce qu'on obtient. Si le déclenchement est automatique, dire à quoi il se
reconnaît.

## Limites

Ce que le skill ne sait pas faire, et les cas où il est moins efficace. Section obligatoire.
