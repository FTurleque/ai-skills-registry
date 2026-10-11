---
kind: skill
name: install-git-submodule
displayName: Installer un sous-module Git mis à jour automatiquement
description: >-
  Installe dans le dépôt courant un sous-module Git qui suit une branche d'un autre dépôt (le
  dépôt entier, ou la branche d'export d'un dossier publiée par publish-git-submodule), puis met
  en place sa mise à jour automatique : script et workflow GitHub Actions déclenchés par événement
  du producteur, par planification et à la main, qui avancent la référence, lancent les contrôles
  du dépôt et poussent un commit limité à cette référence, sans appel à un modèle d'IA. Un dossier
  cible déjà présent n'est jamais écrasé : il est comparé, sauvegardé, et toute divergence demande
  une décision. À invoquer explicitement : /install-git-submodule url=<dépôt>
  branch=submodule/claude target=.claude auto=true.
version: 1.0.0
status: experimental
category: development
tags:
  - git
  - submodule
  - github-actions
  - automation
  - migration
compatibility:
  - claude-code
requires:
  - git-submodule-common (skill voisin, obligatoire)
  - git>=2.38
  - python>=3.8
  - dépôt distant GitHub (pour l'automatisation)
  - gh CLI (facultatif, requis par le mode pull request)
authors:
  - Fabrice Turleque
license: MIT
argument-hint: "url=<dépôt> branch=<branche> target=<dossier> [auto=true] [schedule=<cron>|none] [check=<commande>] | status"
disable-model-invocation: true
---

# Installer un sous-module Git mis à jour automatiquement

Ce skill modifie le dépôt courant : il ajoute un sous-module, peut migrer un dossier existant, et
installe un workflow qui poussera des commits. Il ne s'exécute que sur demande explicite, et tout
ce qu'il fait passe par un script — ne jamais refaire ses étapes à la main avec
`git submodule add`, `git rm` ou en éditant le workflow.

```text
INSTALL = python "${CLAUDE_SKILL_DIR}/resources/scripts/install.py"    (python3 si python est absent)
UPDATE  = python "${CLAUDE_SKILL_DIR}/resources/scripts/update.py"
```

Les scripts importent le module du dossier voisin `git-submodule-common`, installé à côté de ce
skill. S'il manque, ils s'arrêtent en le disant : le signaler à l'utilisateur, ne rien contourner.

Arguments reçus : `$ARGUMENTS`

## Paramètres

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `url` | obligatoire | dépôt source, de préférence en `https://` ; jamais d'identifiant dans l'URL |
| `branch` | obligatoire | branche à suivre : `main` pour un dépôt entier, `submodule/<dossier>` pour un dossier publié |
| `target` | obligatoire | dossier d'installation, relatif à la racine |
| `auto` | `true` | installer script et workflow de mise à jour |
| `schedule` | `17 */6 * * *` | cron UTC du rattrapage planifié ; `none` pour le retirer |
| `target-branch` | branche par défaut, détectée | branche qui reçoit les commits de mise à jour |
| `mode` | `push` | `pr` : pull request à fusion automatique, pour une branche protégée |
| `check` | — | commande de contrôle lancée avant tout commit (répétable) |
| `push` | demander | pousser le commit d'installation |

Chaque paramètre se transmet au script tel quel, un argument par `clé=valeur`, entre guillemets
s'il contient un espace : `"target=shared libs/docs"`. Ne jamais construire une ligne de commande
par concaténation de texte venu de l'utilisateur.

## Déroulé

1. **Aiguiller.** `status` → `UPDATE status`, puis s'arrêter. Sinon, suite.
2. **Regarder la protection de la branche destinataire**, si `gh` est disponible et authentifié :
   `gh api repos/{owner}/{repo}/rules/branches/<branche>` et
   `gh api repos/{owner}/{repo}/branches/<branche>/protection`. Push direct interdit → lire
   [resources/references/permissions.md](resources/references/permissions.md) et proposer
   `mode=pr`, en disant ce que ce mode exige. Ne jamais désactiver ni contourner une règle. Si la
   protection n'a pas pu être lue, le dire dans le compte rendu.
3. **Simuler.** `INSTALL apply <paramètres> dry-run=true`. Rien n'est écrit.
4. **Traiter un refus** selon le code de sortie :
   - `2` paramètre refusé (chemin hors dépôt, URL avec identifiant, branche invalide) : corriger ;
   - `3` dépôt illisible ou branche absente : le script liste les branches disponibles ; pour un
     dossier, la branche d'export doit d'abord être publiée par `/publish-git-submodule` ;
   - `7` **décision de l'utilisateur requise**. Présenter le texte du script sans le résumer —
     fichiers différents, fichiers propres au projet, sous-module déjà présent avec une autre URL
     ou une autre branche, branche qui produirait `<cible>/<cible>` — puis poser **la seule
     question nécessaire** et relancer avec le paramètre correspondant (`migrate=preserve`,
     `set-url=true`, `set-branch=true`, `allow-nested=true`, `force-ignored=true`). Lire
     [resources/references/migration.md](resources/references/migration.md) avant de proposer
     `migrate=preserve`.
5. **Installer.** `INSTALL apply <paramètres> commit=true`. Le commit local ne contient que
   `.gitmodules`, la référence du sous-module et les fichiers gérés : `.github/submodule-update.json`,
   `.github/submodule-sync/`, `.github/workflows/submodule-update.yml`.
6. **Pousser.** Sans `push=true`, montrer le commit et demander avant `git push`. Branche protégée :
   pull request. Le workflow ne se déclenche qu'une fois présent sur la **branche par défaut**.
7. **Rendre compte**, en séparant ce qui est fait de ce qui reste :
   - sous-module installé, SHA référencé, emplacement de la sauvegarde s'il y a eu migration ;
   - comment cloner : `git clone --recurse-submodules`, ou `git submodule update --init` ;
   - les secrets à créer selon le cas, tirés de permissions.md ;
   - pour la mise à jour sur événement : la commande d'inscription à lancer dans le dépôt source
     (`/publish-git-submodule register name=<publication> consumer=<ce dépôt>`). Le mode planifié
     fonctionne sans elle, et sans aucun droit d'écriture sur le dépôt source.

   Ne jamais écrire que l'automatisation est active : elle ne l'est qu'après une exécution verte du
   workflow sur GitHub.

## Règles

- Le dépôt source fait foi. Rien ne remonte du consommateur vers lui : les fichiers propres au
  projet trouvés dans le dossier cible ne sont jamais envoyés à la source.
- Aucun fichier n'est supprimé sans sauvegarde intégrale préalable, vérifiée par empreinte.
- Un sous-module modifié sur le poste n'est jamais écrasé par une mise à jour.
- Les contrôles (`check`) sont des commandes de **ce** dépôt, écrites dans sa configuration. Ne pas
  y mettre une commande qui exécute du code venu du sous-module sans l'avoir lu : elle tournerait
  dans le workflow. Ils sont lancés sans jeton dans l'environnement.
- Le workflow met à jour le dépôt distant, pas les clones : sur chaque poste, `git pull` puis
  `git submodule update --init`. Aucune tâche planifiée locale n'est créée ; l'option est décrite
  dans automation.md.
- Relancer le skill avec les mêmes paramètres vérifie l'installation sans rien créer.

## À lire selon le besoin

| Fichier | Quand |
|---------|-------|
| [resources/references/migration.md](resources/references/migration.md) | dossier cible existant, sous-module déjà présent, code 7 |
| [resources/references/permissions.md](resources/references/permissions.md) | jetons, dépôts privés, branche protégée, mode `pr` |
| [resources/references/automation.md](resources/references/automation.md) | événement, planification, garde-fous, synchronisation des postes |
| [resources/references/troubleshooting.md](resources/references/troubleshooting.md) | diagnostic, retour à un ancien commit, désactivation |
