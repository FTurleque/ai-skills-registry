# Nom du Plugin

Une phrase qui dit ce que le plugin fait.

## Ce que c'est, exactement

Dire de quels composants il est fait et **qui les déclenche**. Un tableau évite l'ambiguïté :

| Fichier | Ce que c'est | Qui le déclenche |
|---|---|---|
| `hooks/hooks.json` | la partie automatique | Claude Code, sur l'événement X |
| `agents/<nom>.md` | un sous-agent | vous, avec `@<plugin>:<nom>` |
| `SKILL.md` | des instructions | vous, avec `/<plugin>`, ou Claude |
| `resources/` | le code appelé | les composants ci-dessus |

## Comment ça se branche

Les étapes, de l'installation à l'effet observable. Si le plugin agit sans être appelé, dire
exactement quand, et ce que l'utilisateur verra.

## Installation

```bash
claude plugin marketplace add FTurleque/ai-toolkit-registry
claude plugin install <nom>@ai-toolkit-registry
claude plugin list
```

## Réglages

Les options, leurs valeurs par défaut, et où se trouve le fichier de configuration.

## Garde-fous

Ce que le plugin ne fait pas, ce qu'il borne, comment il se comporte en cas d'erreur. Pour un plugin
qui pose un hook, cette section est obligatoire : il s'exécute sans être appelé.

## Limites

Les angles morts connus. Section obligatoire.
