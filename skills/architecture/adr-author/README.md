# Rédaction d'ADR

> Décide d'abord si un ADR est justifié, puis crée ou améliore le bon document — et sait répondre « Aucun nouvel ADR nécessaire ».

## Ce que ça change

Sans le skill, « rédige un ADR pour ça » produit toujours un ADR, y compris pour un champ ajouté ou une convention de nommage, et le corpus devient illisible. Avec lui, toute demande passe par trois questions (quelle décision durable ? quel coût de retour arrière ? pourquoi l'existant ne couvre pas ?) et se termine par une seule de cinq conclusions :

| Conclusion | Ce qui est produit |
|---|---|
| Aucun nouvel ADR nécessaire. | une justification, et l'endroit où le contenu a sa place |
| ADR existant applicable : `<ID>`. | un lien, sans recopie |
| Clarification de `<ID>`. | une modification éditoriale qui ne change pas le choix |
| Nouvel ADR proposé. | un brouillon au statut *proposé* |
| Remplacement de `<ID>` proposé. | un nouveau document et des liens réciproques ; l'ancien n'est pas réécrit |

Claude prépare, une personne accepte : le passage à *accepté* et le remplacement d'une décision acceptée attendent une validation humaine.

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/adr-author/` | oui (Windows 10, Claude Code 2.1.292) |
| Claude Code, portée projet | `<projet>/.claude/skills/adr-author/` | non vérifié |

```bash
cp -r skills/architecture/adr-policy skills/architecture/adr-author ~/.claude/skills/
```

Le dossier `adr-policy` est **obligatoire** et doit être installé à côté. Sous Windows, `~` est `%USERPROFILE%`. Voir [docs/install.md](../../../docs/install.md).

Prérequis facultatifs : `git`, Python 3.8+, CLI `archgate` et `openspec` s'ils sont utilisés par le projet. Le skill ne les installe pas et ne crée pas de registre d'ADR de lui-même.

## Usage

```text
/adr-author <besoin en texte libre>          évalue, conclut, propose dans la conversation
/adr-author <nom d'un changement OpenSpec>   revue d'impact architectural du changement
/adr-author <identifiant d'ADR>              améliore ce document
/adr-author <…> rédiger                      écrit le brouillon ou la clarification dans le registre
```

Sans `rédiger` ni demande explicite d'écriture, aucun fichier n'est modifié. Ces arguments sont une convention du skill, pas des options de Claude Code.

Quand c'est Claude qui déclenche le skill, Claude Code peut demander l'autorisation de l'utiliser. Observé en mode non interactif (`claude -p "/adr-… "`) : dans une partie des sessions la commande a été développée directement, dans les autres Claude a dû appeler l'outil `Skill`, qui a été refusé tant qu'il n'était pas autorisé (`--allowedTools Skill`). La cause de cette différence n'a pas été établie.

Exemples réels de quatre des cinq conclusions : [examples/verdicts.md](examples/verdicts.md).

## Limites

- **Le filtre est un jugement argumenté**, pas un calcul : deux lectures peuvent diverger sur un cas limite. Le skill montre son raisonnement pour qu'on puisse le contester.
- **Il ne connaît que ce qui est écrit.** Une décision prise oralement, ou documentée hors du dépôt, lui échappe : il peut proposer un ADR qui existe ailleurs.
- **Il ne vérifie pas le code** : la section « vérification » d'un brouillon cite les contrôles qui existent, elle ne les exécute pas (voir `adr-check`).
- **Sans registre d'ADR dans le projet**, il s'arrête au brouillon dans la conversation et à une proposition d'emplacement.
- **La garde contre la réécriture silencieuse repose sur les instructions**, pas sur une protection technique des fichiers : la revue de PR reste le contrôle effectif.
- **Recoupement avec d'autres skills de rédaction d'ADR** (par exemple un skill d'architecture fourni par un plugin) : celui-ci est le seul à appliquer le filtre de pertinence ; l'invoquer explicitement par `/adr-author` en cas de doute.
- **Essayé sur un petit projet de test**, pas encore sur une application réelle.
- **Surface `claude-code` seule**. Le front matter porte des champs propres au registre, tolérés par Claude Code.
