---
kind: skill
name: adr-check
displayName: Contrôle des ADR
description: >-
  Contrôle le respect des ADR (Architecture Decision Records) dans le code et la cohérence
  documentaire. Deux modes : contrôle d'un changement (diff, branche, changement OpenSpec) et audit
  global. Identifie les ADR applicables, exécute les règles Archgate réellement configurées et les
  tests du projet (ArchUnit s'il existe), vérifie les liens et les vues arc42 touchées. Distingue
  violation prouvée, suspicion issue de la revue et absence de contrôle ; liste les contrôles non
  exécutés ; ne prend jamais une exécution sans règle pertinente pour une conformité. À utiliser
  pour « vérifie que ce changement respecte nos ADR », « contrôle les décisions d'architecture »,
  « lance archgate », avant une PR ou l'archivage d'un changement OpenSpec. Ne modifie ni les
  décisions ni les contrôles.
version: 1.0.0
status: experimental
category: architecture
tags:
  - adr
  - architecture
  - compliance
  - archgate
  - archunit
  - arc42
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
argument-hint: "[changement | global] [base=<ref>] [<nom du changement OpenSpec>]"
allowed-tools: Read Grep Glob Bash(git status *) Bash(git log *) Bash(git diff *) Bash(git ls-files*) Bash(git rev-parse *) Bash(archgate --version) Bash(openspec --version) Bash(git merge-base *) Bash(archgate adr list*) Bash(archgate adr show *) Bash(archgate doctor*) Bash(archgate review-context*) Bash(openspec list*) Bash(openspec show *)
---

# Contrôle des ADR

Dire, preuves à l'appui, ce qui a été vérifié, ce qui est violé, et ce que personne ne contrôle. Ce skill **n'écrit rien** dans les décisions, les règles ou les tests.

Arguments (convention de ce skill, pas une option de Claude Code ni d'Archgate) : `$ARGUMENTS`

| Argument | Effet |
|---|---|
| `changement` *(défaut)* | contrôle le travail en cours : diff avec la branche de base, plus l'arbre de travail |
| `global` | audit de tout le dépôt, indépendant du diff |
| `base=<ref>` | référence de comparaison du mode `changement` ; à défaut celle du projet |
| `<nom d'un changement OpenSpec>` | mode `changement`, avec les ADR et vues que ce changement cite |

## Ressources partagées

Dossier `adr-policy`, voisin de ce skill : `${CLAUDE_SKILL_DIR}/../adr-policy/resources/` (à défaut `~/.claude/skills/adr-policy/resources/`). Lire `discovery.md`, `verification.md` et — si le projet a un dossier `.archgate/` — **`archgate.md` avant toute commande `archgate check`** ; `arc42-openspec.md` et `templates/reports.md` pour la suite. Si le dossier est introuvable, le signaler (installation incomplète) et poursuivre avec les règles ci-dessous.

## Règles

1. **Trois catégories, jamais mélangées** : *violation prouvée* (un contrôle exécuté a échoué, ou `fichier:ligne` contre une contrainte écrite sans ambiguïté) · *suspicion (revue IA)* (lecture qui suggère un écart, sans contrôle qui le démontre) · *absence de contrôle* (rien ne couvre la contrainte).
2. **Un code de sortie 0 ne prouve rien tant qu'on n'a pas compté les règles exécutées.** Une exécution sans règle pertinente n'est pas une conformité démontrée.
3. **Un contrôle de changement n'est pas un audit complet**, et ne se présente jamais comme tel.
4. **Tout contrôle non exécuté est listé avec sa raison** : outil absent, build impossible, sauté par la sélection par diff, ignoré.
5. **Rien n'est affaibli ni réécrit** : pas de règle assouplie, de test désactivé, de périmètre réduit, de décision ajustée au code. Une correction se propose, elle ne s'applique pas ici.
6. **Rien n'est supposé du projet**, et aucun composant manquant n'est installé ni initialisé.
7. « Conforme » s'écrit par contrainte, avec le contrôle nommé qui a tourné sur le périmètre nommé — jamais en synthèse générale.

## Déroulé

0. **Découvrir** le contexte (`discovery.md`) : instructions locales, état Git et branche de base, **tous** les modules, registre d'ADR, règles Archgate, tests d'architecture, commandes de build et de test du projet, CI.
1. **Délimiter** : en mode `changement`, lister les fichiers modifiés (`git diff --name-only <base>...HEAD`, plus `git status --short`) ; en mode `global`, noter l'état contrôlé (commit, arbre propre ou non).
2. **Identifier les ADR applicables** en lisant leur périmètre (modules, motifs `files`, sujet) — tous les ADR en mode `global`. Un ADR peut s'appliquer sans que son motif de fichiers soit touché (un nouveau module, par exemple) : le jugement prime sur le motif. `archgate review-context` aide ; il ne remplace pas la lecture.
3. **Exécuter les règles Archgate** si `.archgate/` existe et que le CLI répond :
   - `changement` : `archgate check --verbose --output json` (ou `--base <ref>`) ;
   - `global` : diff vide exigé — arbre propre et `archgate check --base HEAD --verbose --output json` ; si l'arbre est sale, ne pas le nettoyer : arbre de travail Git temporaire détaché, puis le retirer (procédure dans `archgate.md`). L'audit porte alors sur `HEAD`, pas sur le travail non commité.
   - Dans les deux cas, lire `total`, `passed`, `failed`, `results`, et comparer `total` au nombre de règles attendues. **`total: 0` = aucune règle exécutée.** Un ADR applicable dont la règle a été sautée va dans « non exécuté ».
4. **Exécuter les tests pertinents du projet**, avec la commande que le projet documente (build Maven ou Gradle pour ArchUnit, etc.). Vérifier quels modules et quelles classes ils couvrent réellement. Si la commande est longue, coûteuse ou a des effets (base de données, réseau, déploiement), demander avant de la lancer ; si elle ne peut pas tourner, la consigner « non exécutée ».
5. **Vérifier la documentation** : liens des ADR, index arc42 §9 (`adr_tool.py check --root <racine>` si Python est là), vues arc42 touchées par le changement (`arc42-openspec.md`), références dans les artefacts OpenSpec.
6. **Relire le changement contre les contraintes non automatisées** des ADR applicables. Ce qui en sort est une *suspicion*, sauf preuve `fichier:ligne` contre un texte sans ambiguïté.
7. **Restituer** selon `templates/reports.md` : ADR applicables, contrôles avec commande, résultat et **couverture réelle** (modules, fichiers, règles, tests), les trois catégories, les non-exécutés, les vues à mettre à jour.

## Avant d'archiver un changement OpenSpec

Mode `changement` sur ce changement, plus la grille « Avant d'archiver » de `arc42-openspec.md` : cohérence entre code, décisions, vues arc42 et preuves de contrôle ; architecture actuelle et architecture cible explicitement distinguées.

## Limites

Le skill ne vaut que par les contrôles qui existent : une contrainte sans règle ni test reste une question de revue. Les règles Archgate sur du Java sont textuelles ; les dépendances réelles relèvent d'ArchUnit. Un contrôle exécuté ici ne remplace pas son exécution en CI.
