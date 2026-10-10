# Audit des ADR

> Fait le point sur toutes les décisions d'architecture d'un projet : ce qui existe, ce qui est encore vrai, ce qui se contredit, ce qui manque.

## Ce que ça change

Sans le skill, « audite nos ADR » donne une relecture du premier dossier trouvé, où le statut écrit est pris pour la réalité. Avec lui :

- **tous** les emplacements d'ADR sont inventoriés, pas seulement le registre officiel ;
- le statut déclaré et ce que montrent le code, arc42 et OpenSpec sont deux colonnes distinctes ;
- chaque document reçoit une recommandation : conserver, clarifier, regrouper, remplacer, reclasser, faire confirmer ;
- les décisions structurantes non documentées sont proposées **à confirmer**, jamais créées d'office ;
- rien n'est modifié sans demande explicite, et un changement de sens d'une décision acceptée attend toujours une validation humaine.

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/adr-audit/` | oui (Windows 10, Claude Code 2.1.292) |
| Claude Code, portée projet | `<projet>/.claude/skills/adr-audit/` | non vérifié |

```bash
cp -r skills/architecture/adr-policy skills/architecture/adr-audit ~/.claude/skills/
```

Le dossier `adr-policy` est **obligatoire** et doit être installé à côté : le skill y lit la politique et les gabarits. Sous Windows, `~` est `%USERPROFILE%`. Voir [docs/install.md](../../../docs/install.md).

Prérequis facultatifs : `git`, Python 3.8+ (inventaire automatique), CLI `archgate` et `openspec` s'ils sont utilisés par le projet. Le skill ne les installe pas et n'initialise rien.

## Usage

```text
/adr-audit                    audit de tout le projet, lecture seule
/adr-audit storage            limité à un module, un dossier ou un identifiant d'ADR
/adr-audit appliquer          audit, puis corrections éditoriales non ambiguës
```

Ou en langage naturel : « audite les ADR », « nos décisions d'architecture sont-elles à jour ? ». Ces arguments sont une convention du skill, pas des options de Claude Code.

Quand c'est Claude qui déclenche le skill, Claude Code peut demander l'autorisation de l'utiliser. Observé en mode non interactif (`claude -p "/adr-… "`) : dans une partie des sessions la commande a été développée directement, dans les autres Claude a dû appeler l'outil `Skill`, qui a été refusé tant qu'il n'était pas autorisé (`--allowedTools Skill`). La cause de cette différence n'a pas été établie.

On obtient, dans la conversation : le contexte découvert, l'inventaire (identifiant, emplacement, statut déclaré, réalité observée, contrôles, recommandation), les constats avec leurs preuves, les décisions non documentées à confirmer, les actions applicables et celles à faire valider, la couverture de l'audit. Exemples réels : [examples/audit-reports.md](examples/audit-reports.md).

## Limites

- **L'audit ne prouve pas la conformité.** Il sonde le code pour confronter un statut à la réalité ; le contrôle systématique est le rôle de `adr-check`.
- **Couverture partielle sur un grand dépôt** : le skill dit ce qu'il a examiné et ce qu'il n'a pas vu, il ne le comble pas.
- **Les décisions non écrites restent invisibles** si le code ne les trahit pas, et celles qu'il relève sont des hypothèses.
- **Les raisons historiques ne se retrouvent pas** : quand un statut ou un motif est impossible à établir, la recommandation est « faire confirmer ».
- **Essayé sur un petit projet de test et sur un dépôt sans ADR**, pas encore sur une application réelle avec un historique de décisions : voir les exemples.
- **Surface `claude-code` seule** : le skill lit le dépôt et lance des commandes.
- **Front matter du registre** : `SKILL.md` porte des champs propres au registre (`kind`, `displayName`, `tags`, `status`…) que Claude Code tolère ; un téléversement plus strict pourrait les refuser (non vérifié).
