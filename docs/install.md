# Installer un artefact du registre

Chaque type d'artefact s'installe à sa façon. Ce document donne la procédure exacte, type par type,
et les emplacements par surface.

---

## Les deux portées

| Portée | Emplacement | Effet |
|--------|-------------|-------|
| Utilisateur | `~/.claude/` | tous vos projets |
| Projet | `<projet>/.claude/` | ce dépôt seulement, et partageable avec l'équipe si versionné |

Sous Windows, `~` est `%USERPROFILE%`, donc `C:\Users\<vous>\.claude\`.

---

## Plugins

La seule installation automatisée, parce que le dépôt est une marketplace.

```bash
claude plugin marketplace add FTurleque/ai-toolkit-registry
claude plugin install <nom>@ai-toolkit-registry

claude plugin list                  # vérifier
claude plugin details <nom>         # voir ce qu'il apporte
claude plugin update <nom>@ai-toolkit-registry
claude plugin uninstall <nom>@ai-toolkit-registry
```

Depuis un clone local, pour essayer avant publication :

```bash
claude plugin marketplace add .
claude plugin install <nom>@ai-toolkit-registry
```

Un plugin ne modifie pas votre `settings.json` : il porte lui-même la déclaration de ses hooks, de
ses sous-agents et de ses commandes. Le désinstaller les retire tous.

---

## Skills

| Surface | Emplacement |
|---------|-------------|
| Claude Code, portée utilisateur | `~/.claude/skills/<nom>/` |
| Claude Code, portée projet | `<projet>/.claude/skills/<nom>/` |
| Application de bureau | les réglages de l'application, ou via un plugin |
| claude.ai | téléverser le dossier dans les skills du compte ou du projet |
| API / Agent SDK | pointer le chemin du dossier dans la configuration de l'agent |

```bash
cp -r skills/development/java-code-review ~/.claude/skills/
```

Copier le dossier **entier** : `SKILL.md` seul perd les `resources/` et les `examples/` auxquels il
renvoie.

---

## Sous-agents

```bash
cp agents/<nom>.md ~/.claude/agents/
```

Invocation : `@<nom>`. Pour un sous-agent livré par un plugin : `@<plugin>:<agent>`.

---

## Commandes

```bash
cp commands/<nom>.md ~/.claude/commands/
```

Invocation : `/<nom>`, ou `/<plugin>:<commande>` pour une commande livrée par un plugin.

---

## Hooks

Un hook autonome se déclare dans un `settings.json`. Fusionner l'extrait `settings.hooks.json` de
l'artefact dans `~/.claude/settings.json` ou `<projet>/.claude/settings.json`, **sans écraser les
hooks déjà présents** : la structure est `hooks` → événement → liste de groupes → liste de
handlers, et plusieurs handlers peuvent coexister sur un même événement.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "args": ["python", "~/.claude/hooks/mon-hook.py"], "timeout": 60 }
        ]
      }
    ]
  }
}
```

Sauvegarder le fichier avant de le modifier. Quand un hook fait partie d'un outil plus large,
préférer sa version empaquetée en plugin : elle s'installe et se retire proprement.

---

## Instructions de projet

Rien à installer dans `~/.claude`. Copier le gabarit à la racine du dépôt cible et le remplir :

```bash
cp instructions/<nom>/CLAUDE.md /chemin/du/projet/CLAUDE.md
```

Versionner `CLAUDE.md` pour le partager avec l'équipe ; garder `CLAUDE.local.md` hors de git.

---

## Serveurs MCP

| Portée | Emplacement |
|--------|-------------|
| Projet | `<projet>/.mcp.json`, versionné |
| Utilisateur | configuration Claude Code de l'utilisateur |
| Plugin | champ `mcpServers` du `plugin.json` |

Fusionner l'extrait `.mcp.json` de l'artefact, renseigner les secrets **par variables
d'environnement**, puis vérifier dans une nouvelle session que les outils `mcp__<serveur>__*`
apparaissent.

---

## Styles de sortie

```bash
cp output-styles/<nom>.md ~/.claude/output-styles/
```

Puis sélectionner le style dans la session avec `/output-style`.

---

## Vérifier qu'une installation a pris

| Type | Vérification |
|------|--------------|
| Plugin | `claude plugin list`, puis `claude plugin details <nom>` |
| Skill | demander à Claude ce qu'il sait faire sur le sujet de la skill |
| Sous-agent | `@<nom>` doit être proposé à la complétion |
| Commande | `/<nom>` doit apparaître dans la liste des commandes |
| Hook | déclencher son événement et observer son effet, ou ses traces |
| Serveur MCP | les outils `mcp__<serveur>__*` sont disponibles dans la session |
| Style de sortie | `/output-style` doit le lister |

---

## Désinstaller

Un plugin : `claude plugin uninstall <nom>@ai-toolkit-registry`.

Tout le reste a été copié à la main : supprimer le fichier ou le dossier à son emplacement
d'installation. Pour un hook, retirer en plus son handler du `settings.json`.
