# Contrôle des ADR

> Vérifie que le code respecte les décisions d'architecture, et dit exactement ce qui a été contrôlé — et ce qui ne l'a pas été.

## Ce que ça change

Sans le skill, « vérifie les ADR » se résume souvent à lancer une commande et à lire son code de sortie. Or un contrôle peut être vert sans avoir rien exécuté : avec Archgate 0.59.0, il suffit qu'un fichier **sans rapport** soit modifié pour que les règles d'un ADR soient sautées (`pass: true`, `total: 0`, code 0), même si une violation existe déjà. Avec le skill :

- les ADR applicables sont identifiés par leur périmètre, pas seulement par les motifs de fichiers ;
- les règles Archgate configurées et les tests du projet (ArchUnit s'il existe) sont exécutés, et **le nombre de règles réellement exécutées est compté** ;
- deux modes distincts : contrôle d'un changement (diff) et audit global — le premier ne se fait jamais passer pour le second ;
- les résultats sont rangés en trois catégories : violation prouvée, suspicion issue de la revue, absence de contrôle ;
- tout contrôle non exécuté est listé avec sa raison ;
- rien n'est corrigé, assoupli ni réécrit.

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/adr-check/` | oui (Windows 10, Claude Code 2.1.292) |
| Claude Code, portée projet | `<projet>/.claude/skills/adr-check/` | non vérifié |

```bash
cp -r skills/architecture/adr-policy skills/architecture/adr-check ~/.claude/skills/
```

Le dossier `adr-policy` est **obligatoire** et doit être installé à côté. Sous Windows, `~` est `%USERPROFILE%`. Voir [docs/install.md](../../../docs/install.md).

Prérequis facultatifs : `git` (sélection par diff), CLI `archgate` (règles), l'outil de build du projet (tests), Python 3.8+ (liens et index). Ce qui manque est signalé comme « non exécuté » ; rien n'est installé.

## Usage

```text
/adr-check                        contrôle du travail en cours (diff avec la branche de base)
/adr-check base=origin/develop    idem, avec une autre référence
/adr-check add-order-export       idem, avec les ADR et vues cités par ce changement OpenSpec
/adr-check global                 audit de tout le dépôt, indépendant du diff
```

Ces arguments sont une convention du skill, pas des options de Claude Code ni d'Archgate. Les commandes qui exécutent du code du projet (`archgate check`, build, tests) demandent l'autorisation habituelle de Claude Code : le skill ne pré-autorise que des lectures.

Quand c'est Claude qui déclenche le skill, Claude Code peut demander l'autorisation de l'utiliser. Observé en mode non interactif (`claude -p "/adr-… "`) : dans une partie des sessions la commande a été développée directement, dans les autres Claude a dû appeler l'outil `Skill`, qui a été refusé tant qu'il n'était pas autorisé (`--allowedTools Skill`). La cause de cette différence n'a pas été établie.

Exemple réel : [examples/check-reports.md](examples/check-reports.md).

## Limites

- **Le skill ne vaut que par les contrôles qui existent.** Une contrainte sans règle ni test reste une affaire de revue ; il le dit, il ne la vérifie pas.
- **Le comportement d'Archgate décrit est celui de la version 0.59.0**, observé sous Windows 10. Une autre version peut sélectionner les ADR autrement : le skill demande de compter les règles exécutées plutôt que de se fier à la documentation.
- **L'audit global par arbre de travail temporaire contrôle `HEAD`**, pas le travail non commité.
- **Les règles Archgate sur du Java sont textuelles** (pas d'analyse syntaxique Java dans l'outil) : les dépendances réelles relèvent d'ArchUnit, que le skill exécute s'il est présent mais n'écrit pas.
- **ArchUnit n'a pas été exercé pendant la mise au point** : le projet de test n'avait pas de build exécutable. La consigne (commande du projet, modules réellement couverts) est écrite, son application reste à éprouver sur une vraie application Java.
- **Une suspicion issue de la revue n'est pas une preuve**, dans un sens comme dans l'autre.
- **Un contrôle lancé ici ne remplace pas son exécution en CI.**
- **Surface `claude-code` seule**. Le front matter porte des champs propres au registre, tolérés par Claude Code.
