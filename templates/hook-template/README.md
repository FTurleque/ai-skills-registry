# Nom du Hook

Une phrase : quel événement, quel effet.

## Événement et déclenchement

| Événement | Quand il se produit | Peut bloquer |
|-----------|---------------------|--------------|
| `PostToolUse` | après un appel d'outil réussi | non |

Dire précisément à quoi se reconnaît un déclenchement, et à quelle fréquence il faut s'y attendre.

## Effets de bord

Ce que le hook lit, ce qu'il écrit, où. Ce qu'il bloque, et dans quels cas. **Section obligatoire** :
un hook s'exécute sans être appelé, donc l'utilisateur doit savoir exactement ce qu'il accepte.

## Installation

Fusionner `settings.hooks.json` dans `~/.claude/settings.json` ou `<projet>/.claude/settings.json`,
en conservant les handlers déjà présents, puis copier le script :

```bash
cp -r hooks/<nom> ~/.claude/hooks/
```

## Garde-fous

Temps borné, absence de boucle, absence de récursion, comportement en cas d'erreur.

## Limites

Les cas que le hook ne couvre pas. Section obligatoire.
