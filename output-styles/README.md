# Styles de sortie

Un **style de sortie** change la façon dont Claude Code s'exprime et se comporte, en remplaçant une
partie de son prompt système par le vôtre. Ce n'est pas un thème : c'est un changement de posture
— plus pédagogue, plus laconique, orienté revue, orienté rédaction.

À distinguer d'une skill, qui s'active pour une tâche : un style de sortie est actif en permanence
jusqu'à ce que vous le changiez.

## Forme attendue

Artefact **mono-fichier** : `output-styles/<nom>.md`. Métadonnées dans le front matter.

```markdown
---
kind: output-style
name: mon-style
displayName: Mon Style
description: La posture que ce style impose et dans quel contexte l'utiliser.
version: 1.0.0
status: stable
category: writing
tags: [concision]
compatibility: [claude-code, claude-desktop]
authors: [Fabrice Turleque]
license: MIT
---

Le corps décrit le comportement attendu : ton, niveau de detail,
structure des reponses, ce qu'il faut faire et ne pas faire.
```

## Installation

| Portée | Emplacement |
|--------|-------------|
| Tous vos projets | `~/.claude/output-styles/<nom>.md` |
| Un seul projet | `<projet>/.claude/output-styles/<nom>.md` |

Puis sélectionner le style dans la session (`/output-style`).

## Avertissement

Un style de sortie remplace une partie du prompt système de l'outil. Un style trop prescriptif peut
dégrader la capacité de Claude à faire son travail — supprimer la vérification, encourager la
complaisance, raccourcir au point de perdre l'information utile. Un style décrit **comment**
répondre, jamais **quoi** conclure.
