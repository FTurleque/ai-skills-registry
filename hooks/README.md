# Hooks

Un **hook** est un bout de code que Claude Code exécute **à un événement**, sans que personne le
demande : avant un appel d'outil, après une écriture de fichier, à la fin d'une réponse d'agent, au
démarrage d'une session. C'est le seul mécanisme du dépôt qui agit sans être invoqué — et le plus
puissant pour cette raison même.

Les hooks de ce dossier sont **autonomes** : réutilisables tels quels, déclarés dans un
`settings.json`. Un hook qui fait partie d'un outil plus large appartient à un plugin, où il est
déclaré dans `hooks/hooks.json` et installé avec lui — c'est la voie à préférer, parce qu'elle ne
touche pas aux réglages de l'utilisateur.

## Forme attendue

```text
hooks/<nom-du-hook>/
├── metadata.yaml        métadonnées du registre (obligatoire)
├── README.md            événement visé, effet, risques, installation (obligatoire)
├── settings.hooks.json  extrait à fusionner dans un settings.json (obligatoire en pratique)
├── <script>             le code exécuté (.py, .sh, .ps1)
└── examples/            entrée et sortie réelles du hook
```

## Les événements

| Événement | Quand | Peut bloquer |
|-----------|-------|--------------|
| `PreToolUse` | avant un appel d'outil | oui |
| `PostToolUse` | après un appel d'outil réussi | non, mais peut enrichir le résultat |
| `UserPromptSubmit` | à l'envoi d'un message | oui |
| `Stop` | quand l'agent principal termine sa réponse | oui |
| `SubagentStop` | quand un sous-agent termine | oui |
| `SessionStart` / `SessionEnd` | ouverture et fermeture de session | non |

## Règles de prudence

Un hook tourne à chaque occurrence de son événement, sur tous les projets concernés par le
`settings.json` qui le déclare. Donc :

- **Toujours borner le temps** : un `timeout` explicite, et un script qui rend la main vite.
- **Jamais de boucle** : un hook bloquant qui se redéclenche sur sa propre action gèle la session.
  Les hooks `Stop` reçoivent `stop_hook_active: true` quand il est temps de s'arrêter — le
  respecter n'est pas facultatif.
- **Jamais de récursion** : un hook qui relance Claude doit désactiver les hooks dans l'appel fils
  (`CLAUDE_CODE_DISABLE_HOOKS=1`) et poser sa propre variable de garde.
- **Dégradation propre** : une erreur interne du hook ne doit jamais empêcher la session de
  continuer. En cas de doute, sortir en 0 sans rien dire.
- **Documenter l'effet de bord** : le README doit dire ce que le hook écrit, où, et ce qu'il bloque.

## Installation

Fusionner l'extrait `settings.hooks.json` dans `~/.claude/settings.json` (toutes les sessions) ou
`<projet>/.claude/settings.json` (un projet). Les hooks existants doivent être conservés : la
structure est `hooks` → nom de l'événement → liste de groupes → liste de handlers.
