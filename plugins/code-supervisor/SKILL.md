---
kind: plugin
name: code-supervisor
displayName: Code Supervisor
description: Supervision automatique du code produit par un agent, avec renvoi en correction sur probleme bloquant. A utiliser pour relire un diff ou un ensemble de fichiers et rendre un verdict sur la securite, les bugs introduits, la duplication, la complexite, le nommage et les conventions du projet.
version: 1.1.0
status: experimental
category: development
tags:
  - code-review
  - quality
  - security
  - duplication
  - complexity
  - naming
  - hook
  - automation
compatibility:
  - claude-code
  - claude-desktop
requires:
  - python>=3.8
  - git
authors:
  - Fabrice Turleque
license: MIT
---

# Objectif

Relire le code qui vient d'etre modifie et rendre un verdict exploitable : ce qui est faux, ou,
et quoi faire. En declenchement automatique, un probleme bloquant renvoie l'agent corriger avant
qu'il ne rende la main. En usage manuel, le verdict est rendu a l'utilisateur.

Ce skill ne corrige jamais le code lui-meme.

# Cas d'utilisation

- Relecture automatique apres chaque implementation par un agent (hooks `Stop` et `SubagentStop`)
- Relecture a la demande d'un diff en cours, avant commit ou avant ouverture d'une pull request
- Audit cible d'un fichier ou d'un module precis
- Garde-fou sur un depot ou plusieurs agents travaillent en parallele

# Entrees attendues

- **Perimetre** : rien a fournir en declenchement automatique — l'etat git et les fichiers ecrits
  pendant la session determinent le perimetre. En usage manuel, une liste de chemins facultative.
- **Conventions du projet** : lues automatiquement si presentes (`CLAUDE.md`, `CONTRIBUTING.md`,
  `AGENTS.md`, `.editorconfig`), et a defaut deduites du code voisin.
- **Seuils** : repris de `supervisor.config.json` ; aucune saisie necessaire.

# Instructions

Determiner le perimetre, puis juger uniquement ce qui a change.

1. Perimetre : `git status --porcelain` et `git diff` (plus `git diff --cached`). Un fichier neuf
   est lu en entier ; pour un fichier modifie, seules les lignes du diff et les fonctions qui les
   contiennent sont jugees. Le code non touche n'est pas mis en cause.
2. Analyse statique, qui traite ce qui se mesure :
   `python <racine>/resources/supervisor.py --check [chemins...]`
3. Lire les conventions du projet avant de juger le style. Le code voisin du diff est la
   reference reelle, les fichiers de conventions la reference declaree.
4. Juger ce que l'analyse statique ne sait pas juger :
   - bug de logique, cas limite casse, contrat d'API rompu ;
   - regression chez un appelant existant — chercher les appelants avant de conclure ;
   - nom qui ne decrit pas ce qu'il est, ou qui ment sur son effet ;
   - reimplementation de quelque chose qui existe deja dans le depot ;
   - complexite evitable : methode qui fait plusieurs choses, abstraction inutile.
5. Classer chaque constat : `CRITICAL` si le code est faux, dangereux ou casse l'existant ;
   `MAJOR` pour un defaut de qualite reel sans danger immediat ; `MINOR` pour une amelioration
   souhaitable.
6. Verifier chaque `CRITICAL` en lisant le code concerne avant de le retenir.

# Contraintes

- Ne jamais modifier un fichier : ce skill rend un verdict, il ne corrige pas.
- Ne jamais proposer de neutraliser un controle (`@SuppressWarnings`, `// NOSONAR`, `# noqa`,
  `@ts-ignore`, test desactive) pour faire disparaitre un constat. Ces neutralisations sont
  elles-memes des constats.
- Ne pas remonter de remarque de forme que l'outillage automatique traite deja.
- Ne pas juger du code hors du perimetre, sauf si le diff le casse.
- Un faux positif coute plus cher qu'un oubli : il envoie l'agent modifier du code correct.
  En cas de doute, classer plus bas plutot que bloquer.
- Ne lancer aucun build ni aucune CI. Les outils ne sont appeles que s'ils sont declares dans
  `external_tools`, et cette liste est vide par defaut. Seule la configuration de l'utilisateur ou
  celle du moteur est honoree : une configuration de projet ne peut pas lancer de programme.

# Processus d'execution

1. Delimiter le perimetre (etat git, fichiers ecrits pendant la session).
2. Lancer l'analyse statique sur ce perimetre.
3. Lire les conventions du projet et le code voisin.
4. Relire le diff et verifier les points candidats au blocage.
5. Fusionner les constats, dedupliquer, trier par severite.
6. Rendre le verdict : bloquant s'il reste au moins un `CRITICAL`, sinon avertissement.

# Format de sortie

```
- <SEVERITE> / <categorie> — <fichier>:<ligne> (<symbole>)
  - Probleme : ce qui est faux, en une phrase
  - A faire : l'action precise attendue
  - Code : l'extrait concerne

Verdict : bloquant | non bloquant — <n> critical, <n> major, <n> minor
```

Categories utilisees : `securite`, `bug`, `duplication`, `complexite`, `nommage`, `convention`.

# Criteres de validation

- [ ] Chaque constat porte un fichier et une ligne verifiables
- [ ] Chaque constat dit quoi faire, pas seulement ce qui ne va pas
- [ ] Aucun constat ne porte sur du code non touche par le diff
- [ ] Chaque `CRITICAL` a ete verifie dans le code avant d'etre retenu
- [ ] Aucun fichier n'a ete modifie par la relecture
- [ ] Aucun build ni aucune CI n'a ete declenche

# Exemples

Voir `examples/example.md` pour un diff fautif, le verdict rendu et le message transmis a l'agent.

# Limites

- La couche statique raisonne sur des motifs, pas sur un arbre syntaxique complet : elle peut
  manquer un cas exotique de mise en forme, et ne suit pas les flux de donnees entre fichiers.
- La detection de duplication compare des structures de lignes normalisees : une duplication
  reecrite differemment lui echappe.
- Le jugement sur le nommage et les conventions depend de la couche modele. Sans la CLI `claude`
  disponible, seule la couche statique s'applique.
- Elle ne remplace pas les tests : un bug de logique que ni le modele ni les motifs ne voient
  passe. C'est un garde-fou supplementaire, pas une garantie.
- Pour une revue Java approfondie et manuelle, voir le skill partage
  [`java-code-review`](../../skills/development/java-code-review/README.md), dont la grille est
  complementaire : elle est pensee pour une relecture humaine exhaustive, la ou ce skill cible le
  diff d'une session agent.
