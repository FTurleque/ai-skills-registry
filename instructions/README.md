# Instructions de projet

Les fichiers de **contexte projet** : ce que Claude lit automatiquement au démarrage d'une session
dans un dépôt, sans qu'on le lui demande. C'est l'endroit où vivent les conventions d'une base de
code, ses commandes de build, ses pièges et ses règles non écrites.

Le contenu le plus transversal du registre : un bon gabarit de `CLAUDE.md` se réutilise sur tous
vos dépôts, et c'est souvent lui qui fait la plus grande différence sur la qualité du travail d'un
agent.

## Forme attendue

```text
instructions/<nom-du-jeu>/
├── metadata.yaml   métadonnées du registre (obligatoire)
├── README.md       à quel type de projet ça s'applique, et pourquoi (obligatoire)
├── CLAUDE.md       le gabarit lui-même
└── examples/       une version remplie pour un projet réel
```

Un jeu d'instructions peut porter plusieurs fichiers quand le projet en a besoin : un `CLAUDE.md`
racine et des `CLAUDE.md` par module, par exemple.

## Où Claude les lit

| Fichier | Portée |
|---------|--------|
| `<projet>/CLAUDE.md` | le dépôt, versionné et partagé avec l'équipe |
| `<projet>/CLAUDE.local.md` | le dépôt, mais local — à ignorer dans git |
| `<projet>/<module>/CLAUDE.md` | chargé quand Claude touche ce module |
| `~/.claude/CLAUDE.md` | tous vos projets |
| `<projet>/AGENTS.md` | convention inter-outils, lue par Claude Code et d'autres agents |

## Ce qui fait un bon fichier d'instructions

- Des faits vérifiables, pas des intentions : la commande exacte pour lancer les tests, pas « les
  tests doivent passer ».
- Ce qu'un nouvel arrivant se ferait dire à l'oral le premier jour : le piège qui fait perdre deux
  heures, la règle qui n'est écrite nulle part.
- Court. Ce fichier est chargé à chaque session : chaque ligne inutile coûte du contexte à toutes
  les conversations du dépôt.
- Pas de duplication avec un README : le README explique le projet à un humain, le `CLAUDE.md`
  dit à un agent comment y travailler.

## Installation

Copier le gabarit à la racine du dépôt cible et le remplir. Rien à installer dans `~/.claude`.
