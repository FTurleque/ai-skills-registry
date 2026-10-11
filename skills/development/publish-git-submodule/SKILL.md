---
kind: skill
name: publish-git-submodule
displayName: Publier une source de sous-module Git
description: >-
  Prépare un dépôt entier, ou un seul de ses dossiers (.claude, docs, une bibliothèque), pour être
  installé comme sous-module Git dans d'autres dépôts, puis automatise sa republication. Pour un
  dossier : extrait son contenu à la racine d'une branche d'export du même dépôt distant
  (git subtree split), contrôle fichiers locaux, secrets et chemins personnels avant tout push,
  et installe un workflow GitHub Actions qui republie après chaque push et notifie les dépôts
  consommateurs, sans appel à un modèle d'IA. À invoquer explicitement : /publish-git-submodule
  source=.claude branch=main export=submodule/claude auto=true. Le skill voisin
  install-git-submodule fait l'autre moitié, côté dépôt destinataire.
version: 1.0.0
status: experimental
category: development
tags:
  - git
  - submodule
  - subtree
  - github-actions
  - automation
compatibility:
  - claude-code
requires:
  - git-submodule-common (skill voisin, obligatoire)
  - git>=2.38 avec git subtree
  - python>=3.8
  - dépôt distant GitHub (pour l'automatisation)
  - gh CLI (facultatif)
authors:
  - Fabrice Turleque
license: MIT
argument-hint: "source=<.|dossier> [branch=<branche>] [export=<branche>] [auto=true] | register name=<publication> consumer=<propriétaire/dépôt> | status"
disable-model-invocation: true
---

# Publier une source de sous-module Git

Ce skill publie : il pousse une branche et installe un workflow. Il ne s'exécute que sur demande
explicite, et tout ce qu'il fait passe par un script — ne jamais refaire ses étapes à la main avec
`git subtree`, `git push` ou en éditant le workflow.

```text
SCRIPT = python "${CLAUDE_SKILL_DIR}/resources/scripts/publish.py"     (python3 si python est absent)
```

Le script importe le module du dossier voisin `git-submodule-common`, installé à côté de ce skill.
S'il manque, il s'arrête en le disant : le signaler à l'utilisateur, ne rien contourner.

Arguments reçus : `$ARGUMENTS`

## Paramètres

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `source` | `.` | `.` = dépôt entier ; sinon un dossier relatif à la racine |
| `branch` | branche par défaut du remote, détectée | branche source |
| `export` | `submodule/<dossier>` | branche d'export (mode dossier seulement) |
| `name` | dérivé du dossier | identifiant de la publication |
| `remote` | `origin` | remote du dépôt |
| `auto` | `true` | installer le workflow de republication |
| `strategy` | `subtree` | `snapshot` = export sans historique, seul mode qui accepte `exclude` |
| `exclude` | — | motif retiré de l'export (répétable, `snapshot` seulement) |
| `consumer` | — | dépôt à notifier (répétable) |
| `push` | demander | pousser le commit de configuration sur la branche courante |

Chaque paramètre se transmet au script tel quel, un argument par `clé=valeur`, entre guillemets
s'il contient un espace : `"source=my docs"`. Ne jamais construire une ligne de commande par
concaténation de texte venu de l'utilisateur.

## Déroulé

1. **Aiguiller.** `register …` ou `unregister …` → `SCRIPT register --name … --consumer … --commit`,
   puis étape 6. `status` → `SCRIPT status`, puis s'arrêter. Sinon, suite.
2. **Simuler.** `SCRIPT setup <paramètres> dry-run=true`. Rien n'est écrit ni poussé. Lire le
   résultat : mode (dépôt entier ou dossier), commit source, branche d'export, constats.
3. **Traiter un refus** selon le code de sortie — ne jamais contourner :
   - `2` paramètre ou état refusé (chemin hors dépôt, dossier sans fichier suivi, dossier déjà
     sous-module, collision de branche) : expliquer, corriger le paramètre avec l'utilisateur ;
   - `3` remote ou branche inaccessible : le dire, s'arrêter ;
   - `4` la branche d'export existe et n'est pas un ancêtre : lire
     [references/security-and-history.md](resources/references/security-and-history.md), exposer
     la cause, ne passer `force=true` que sur accord explicite ;
   - `5` contenu sensible : montrer chaque constat (fichier, ligne, « dernier commit » ou
     « historique publié »), puis proposer les trois issues du même document. `accept-findings=true`
     est une décision de l'utilisateur, jamais une initiative.
4. **Publier.** `SCRIPT setup <paramètres> commit=true`. Cette commande pousse la branche d'export
   (ou rien, pour un dépôt entier) et crée un commit local limité aux fichiers gérés :
   `.github/submodule-publish.json`, `.github/submodule-sync/`, `.github/workflows/submodule-publish.yml`.
5. **Pousser la configuration.** Sans `push=true`, montrer le commit et demander avant
   `git push`. Si la branche est protégée, ouvrir une pull request ; ne rien contourner. Le workflow
   n'agit qu'une fois présent sur la branche source, et sur la branche par défaut pour le
   lancement manuel.
6. **Rendre compte**, en séparant ce qui est fait de ce qui reste :
   - branche publiée et son SHA, fichiers créés, commit, état du push ;
   - la commande exacte pour le consommateur, recopiée de la sortie du script
     (`/install-git-submodule url=… branch=… target=… auto=true`) ;
   - si des consommateurs sont inscrits : le secret `SUBMODULE_DISPATCH_TOKEN` à créer
     ([references/automation.md](resources/references/automation.md)).
   Ne jamais écrire que l'automatisation est active : elle ne l'est qu'après une exécution verte du
   workflow sur GitHub, que ce skill ne peut pas observer sans `gh run list`.

## Règles

- Seuls les commits de la branche **distante** sont publiés : ni fichier non suivi, ni commit non
  poussé. Le script le signale ; le dire à l'utilisateur.
- Une extraction subtree publie l'historique du dossier. Retirer un fichier du dernier commit ne
  l'en efface pas.
- Limiter le contenu extrait ne limite ni le téléchargement des objets Git ni les droits d'accès :
  la branche d'export vit dans le même dépôt, qui lit l'une lit l'autre.
- Relancer le skill est sans risque : même configuration, aucun commit, aucun push.
- Ne pas transformer le dépôt courant en consommateur : c'est le rôle de `install-git-submodule`.

## À lire selon le besoin

| Fichier | Quand |
|---------|-------|
| [resources/references/architecture.md](resources/references/architecture.md) | expliquer les deux modes, le flux, plusieurs publications |
| [resources/references/security-and-history.md](resources/references/security-and-history.md) | codes 4 et 5, `snapshot`, `exclude`, réécriture d'historique |
| [resources/references/automation.md](resources/references/automation.md) | workflow, jetons, notification, limites de `GITHUB_TOKEN` |
| [resources/references/troubleshooting.md](resources/references/troubleshooting.md) | diagnostic, reprise, désactivation |
