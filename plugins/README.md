# Plugins

Un **plugin** Claude Code est un paquet installable qui branche des composants sur l'outil. C'est
la seule forme du dépôt qui peut **s'exécuter toute seule** : un plugin peut poser des hooks, qui
se déclenchent sur des événements de session sans que personne les appelle.

Ne pas confondre avec une skill : une skill est un fichier d'instructions que Claude lit ; un
plugin est un paquet qui peut contenir des hooks, des sous-agents, des commandes, des skills, des
serveurs MCP et des styles de sortie. Un plugin peut donc contenir une skill — l'inverse est faux.

## Forme attendue

```text
plugins/<nom-du-plugin>/
├── .claude-plugin/
│   └── plugin.json      manifeste du plugin (obligatoire)
├── metadata.yaml        métadonnées du registre (obligatoire)
├── README.md            ce que c'est, comment l'installer, comment ça se branche (obligatoire)
├── hooks/hooks.json     déclaration des hooks (facultatif)
├── agents/<nom>.md      sous-agents livrés par le plugin (facultatif)
├── commands/<nom>.md    commandes slash livrées par le plugin (facultatif)
├── skills/<nom>/        skills livrées par le plugin (facultatif)
├── SKILL.md             skill unique du plugin, à sa racine (facultatif)
└── resources/           code et données appelés par les composants (facultatif)
```

Règles non négociables :

- Aucun chemin absolu. Le chemin racine du plugin installé est fourni par `${CLAUDE_PLUGIN_ROOT}`,
  et c'est la seule façon correcte de référencer un fichier livré par le plugin.
- Rien d'écrit dans `${CLAUDE_PLUGIN_ROOT}` à l'exécution : ce chemin change à chaque mise à jour.
  L'état persistant va dans `${CLAUDE_PLUGIN_DATA}`.
- Un hook qui lance un script préfère la forme exec (`args`) à la forme shell (`command`) : pas de
  problème de guillemets sous Windows.

## Déclaration dans la marketplace

Le dépôt est une marketplace : chaque plugin doit figurer dans
[`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) à la racine, avec un
`source` relatif à cette racine. Le validateur refuse un plugin non déclaré, et une déclaration
sans plugin.

## Installation

```bash
claude plugin marketplace add FTurleque/ai-toolkit-registry
claude plugin install <nom-du-plugin>@ai-toolkit-registry
claude plugin list
```

Depuis un clone local, pour tester avant publication :

```bash
claude plugin marketplace add .
claude plugin install <nom-du-plugin>@ai-toolkit-registry
```

## Ajouter un plugin

1. `cp -r templates/plugin-template plugins/<nom>/`
2. Remplir `.claude-plugin/plugin.json` et `metadata.yaml`.
3. Déclarer le plugin dans `.claude-plugin/marketplace.json`.
4. `claude plugin validate ./plugins/<nom> --strict` puis `claude plugin validate .`
5. `python tools/validate.py && python tools/generate_index.py`
6. Mettre à jour `CHANGELOG.md` et [docs/surfaces.md](../docs/surfaces.md).
