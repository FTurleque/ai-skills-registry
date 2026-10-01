# Serveurs MCP

Une configuration **MCP** branche un serveur d'outils externes sur Claude : une base de données, un
service interne, une API, un index de code. Claude gagne alors des outils qu'il n'avait pas, nommés
`mcp__<serveur>__<outil>`.

Ce dossier contient des **configurations de branchement** prêtes à l'emploi, pas le code des
serveurs. Un serveur développé ici aurait son propre dépôt ; ce qu'on range ici, c'est ce qu'il
faut écrire pour s'y connecter, et la documentation de ce qu'on y gagne.

## Forme attendue

```text
mcp/<nom-du-serveur>/
├── metadata.yaml   métadonnées du registre (obligatoire)
├── README.md       ce que le serveur apporte, ses prérequis, son branchement (obligatoire)
├── .mcp.json       l'extrait de configuration à fusionner
└── examples/       des appels réels et ce qu'ils renvoient
```

## Les trois portées de configuration

| Portée | Emplacement | Pour qui |
|--------|-------------|----------|
| Projet | `<projet>/.mcp.json`, versionné | toute l'équipe du dépôt |
| Utilisateur | configuration Claude Code de l'utilisateur | tous vos projets |
| Plugin | `mcpServers` dans `plugin.json` | installé avec le plugin |

## Règles

- **Aucun secret dans le fichier de configuration.** Les jetons et mots de passe passent par des
  variables d'environnement, jamais par une valeur littérale. Le validateur du dépôt refuse un
  secret apparent, et c'est une erreur, pas un avertissement.
- Déclarer les prérequis dans `requires` : runtime, binaire, accès réseau, VPN.
- Dire dans le README ce que le serveur **lit et écrit**. Un serveur MCP a les droits du processus
  qui le lance ; c'est une information de sécurité, pas un détail.

## Installation

Fusionner l'extrait dans le `.mcp.json` du projet, ou ajouter le serveur à la configuration
utilisateur, puis vérifier que les outils apparaissent dans la session.
