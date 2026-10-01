# Gabarits

Un gabarit par type d'artefact. Un nouvel artefact part toujours d'une copie de son gabarit : c'est
ce qui garantit que les fichiers obligatoires existent et que les métadonnées sont complètes.

| Type | Gabarit | Commande |
|------|---------|----------|
| skill | `skill-template/` | `cp -r templates/skill-template skills/<catégorie>/<nom>` |
| plugin | `plugin-template/` | `cp -r templates/plugin-template plugins/<nom>` |
| sous-agent | `agent-template.md` | `cp templates/agent-template.md agents/<nom>.md` |
| commande | `command-template.md` | `cp templates/command-template.md commands/<nom>.md` |
| hook | `hook-template/` | `cp -r templates/hook-template hooks/<nom>` |
| instructions | `instructions-template/` | `cp -r templates/instructions-template instructions/<nom>` |
| serveur MCP | `mcp-template/` | `cp -r templates/mcp-template mcp/<nom>` |
| style de sortie | `output-style-template.md` | `cp templates/output-style-template.md output-styles/<nom>.md` |

Après la copie : renommer le champ `name` pour qu'il corresponde au nom du dossier ou du fichier,
sinon la validation échoue. Supprimer les fichiers facultatifs inutilisés plutôt que de les laisser
vides.

Les gabarits ne sont pas des artefacts du registre : ils ne figurent pas dans `INDEX.md` et ne sont
pas validés comme tels. Leur statut est `draft` pour cette raison.
