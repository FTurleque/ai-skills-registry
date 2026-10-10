---
kind: skill
name: adr-author
displayName: Rédaction d'ADR
description: >-
  Décide si un ADR (Architecture Decision Record) est justifié, puis crée ou améliore le bon
  document, à partir d'un besoin, d'un changement OpenSpec ou d'une décision existante. Commence
  toujours par un filtre de pertinence et peut conclure « Aucun nouvel ADR nécessaire ». Selon le
  cas : référence un ADR existant, clarifie un texte sans changer la décision, propose un nouvel
  ADR en brouillon, propose le remplacement explicite d'une décision acceptée, ou oriente vers une
  documentation, une convention ou une tâche. À utiliser pour « faut-il un ADR pour… », « rédige
  un ADR », « documente cette décision d'architecture », « améliore cet ADR », ou pour la revue
  d'impact architectural d'un changement OpenSpec. N'accepte ni ne remplace jamais une décision
  sans validation humaine.
version: 1.0.0
status: experimental
category: architecture
tags:
  - adr
  - architecture
  - decision-record
  - arc42
  - openspec
  - archgate
compatibility:
  - claude-code
requires:
  - adr-policy (skill voisin, obligatoire)
  - git (facultatif)
  - python>=3.8 (facultatif)
  - archgate CLI (facultatif)
  - openspec CLI (facultatif)
authors:
  - Fabrice Turleque
license: MIT
argument-hint: "<besoin | nom du changement OpenSpec | identifiant d'ADR> [rédiger]"
allowed-tools: Read Grep Glob Bash(git status *) Bash(git log *) Bash(git diff *) Bash(git ls-files*) Bash(git rev-parse *) Bash(archgate --version) Bash(openspec --version) Bash(archgate adr list*) Bash(archgate adr show *) Bash(openspec list*) Bash(openspec show *)
---

# Rédaction d'ADR

Un ADR de plus n'est pas un progrès : chaque document doit porter une vraie décision d'architecture. Ce skill filtre d'abord, rédige ensuite.

Arguments (convention de ce skill, pas une option de Claude Code) : `$ARGUMENTS`

| Argument | Effet |
|---|---|
| `<besoin>` en texte libre | évalue la pertinence, conclut, propose le contenu **dans la conversation** |
| `<nom d'un changement OpenSpec>` | revue d'impact architectural de ce changement |
| `<identifiant d'ADR>` | améliore ce document : clarification, ou remplacement si le sens change |
| `rédiger` | écrit le brouillon ou la clarification dans le registre du projet |

Sans `rédiger` ni demande explicite d'écriture (« rédige », « crée le fichier », « applique »), **aucun fichier n'est modifié**.

## Ressources partagées

Dossier `adr-policy`, voisin de ce skill : `${CLAUDE_SKILL_DIR}/../adr-policy/resources/` (à défaut `~/.claude/skills/adr-policy/resources/`). Lire `policy.md` et `discovery.md` avant de commencer ; `templates/adr.md` et `verification.md` pour rédiger ; `arc42-openspec.md` et `archgate.md` selon ce que le projet contient. Si le dossier est introuvable, le signaler (installation incomplète) et poursuivre avec les règles ci-dessous.

## Règles

1. **Le filtre d'abord, toujours.** Pas de brouillon avant d'avoir répondu aux trois questions.
2. **« Aucun nouvel ADR nécessaire. » est une réponse complète**, et souvent la bonne.
3. **Réutiliser avant de créer.** Lire tous les ADR du projet, à tous les emplacements, avant de conclure qu'aucun ne couvre.
4. **Claude prépare, une personne accepte.** Un brouillon naît *proposé*. Le passage à *accepté*, et tout remplacement d'une décision acceptée, exigent une validation humaine explicite.
5. **Une décision acceptée ne se réécrit pas en silence.** Si le sens change, c'est un remplacement : nouveau document, liens réciproques, l'ancien reste.
6. **Aucune raison historique inventée.** Les alternatives sont sourcées, ou présentées comme une analyse datée d'aujourd'hui.
7. **Rien n'est supposé du projet**, et aucun composant manquant n'est installé ni initialisé.

## Déroulé

0. **Découvrir** le contexte (`discovery.md`) : instructions locales, modules, registre(s) d'ADR et leur format, arc42, OpenSpec, Archgate, contrôles existants.
1. **Comprendre la demande.** Pour un changement OpenSpec, lire ses artefacts (`openspec show <nom>` ou les fichiers). La reformuler en une phrase : quelle décision serait prise ?
2. **Lire les ADR existants** et repérer ceux qui touchent le même sujet ou le même périmètre.
3. **Appliquer le filtre** (`policy.md`), par écrit :
   1. Quelle décision durable devons-nous mémoriser, et pourquoi ?
   2. Quel impact, compromis ou coût de retour arrière justifie sa formalisation ?
   3. Pourquoi aucun ADR existant ne la couvre-t-il déjà ?
4. **Conclure** par une seule des cinq conclusions, mot pour mot :

| Conclusion | Suite |
|---|---|
| **Aucun nouvel ADR nécessaire.** | justifier en une ou deux phrases ; orienter le contenu : documentation technique, convention ou règle de linter, tâche ou changement OpenSpec, ticket, vue arc42 |
| **ADR existant applicable : `<ID>`.** | donner le lien et l'effet sur la demande ; ne rien recopier |
| **Clarification de `<ID>`.** | proposer la modification, vérifier qu'elle ne change pas le sens (test : qui appliquait l'ancien texte applique le nouveau sans rien changer) |
| **Nouvel ADR proposé.** | brouillon au statut *proposé*, dans le format du projet, à défaut `templates/adr.md` |
| **Remplacement de `<ID>` proposé.** | exposer la contradiction (les deux textes cités), proposer le remplaçant ; **ne toucher ni à l'ancien ADR ni à son statut** avant validation |

5. **Rendre la décision vérifiable** (`verification.md`) : périmètre sur tous les modules concernés, contraintes observables, contrôles **qui existent réellement**, commande, part de revue humaine. Ne pas déclarer `rules: true` ni citer un test qui n'existe pas.
6. **Relier** : changement OpenSpec, vues arc42 à mettre à jour, ligne à ajouter à l'index §9 — en références, sans copie.
7. **Restituer** selon `templates/reports.md`, en nommant ce qui attend une validation humaine.

## Écrire (`rédiger`)

- Emplacement et format : ceux du registre canonique du projet. Identifiant : le suivant dans sa numérotation ; avec Archgate, `archgate adr create` l'attribue — vérifier son aide avant de l'utiliser.
- **Pas de registre** dans le projet : ne pas en créer un d'office. Présenter le brouillon dans la conversation, proposer un emplacement, attendre le choix.
- Un brouillon peut être écrit sans acceptation préalable ; il porte le statut *proposé* et le dit en tête.
- Clarification d'un ADR accepté : montrer le diff prévu avant d'écrire.
- Mettre à jour l'index arc42 §9 dans la même passe si le projet en a un. Ne rien commiter sans demande.

## Revue d'impact d'un changement OpenSpec

Le workflow et le schéma OpenSpec du projet ne sont pas modifiés. La revue ajoute un bloc « Impact architectural » à l'artefact de conception existant (voir `arc42-openspec.md`) avec l'une des quatre conclusions : aucun nouvel ADR nécessaire · ADR existant applicable · clarification nécessaire · nouvelle décision ou remplacement à proposer. Une vue arc42 peut devoir changer sans nouvel ADR.

## Limites

Le filtre est un jugement argumenté, pas un calcul : il peut être contesté, et c'est à l'équipe de trancher. Le skill ne sait rien des décisions prises oralement et non écrites. Il ne vérifie pas le code (voir `adr-check`).
