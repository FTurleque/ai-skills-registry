---
kind: skill
name: git-submodule-common
displayName: Sous-modules Git (module partagé)
description: >-
  Module Python partagé par les skills publish-git-submodule et install-git-submodule : exécution
  de git sans shell, validation des chemins, branches et URL, authentification par jeton sans
  secret persistant, écriture des fichiers gérés. Ne se déclenche pas seul et ne s'invoque pas : il
  est importé par les scripts des deux autres skills, qui ne fonctionnent pas sans lui.
version: 1.0.0
status: experimental
category: development
tags:
  - git
  - submodule
  - shared
compatibility:
  - claude-code
requires:
  - git>=2.38
  - python>=3.8
authors:
  - Fabrice Turleque
license: MIT
user-invocable: false
disable-model-invocation: true
---

# Sous-modules Git — module partagé

Ce dossier ne fait rien par lui-même. Il porte, en un seul exemplaire, le code que
`publish-git-submodule` et `install-git-submodule` ont en commun, pour qu'il n'en existe pas deux
copies divergentes.

Il s'installe **à côté** des deux skills, dans le même dossier `skills/` : leurs scripts l'importent
par le chemin relatif `../git-submodule-common/resources/scripts/`. Absent, ils s'arrêtent en le
disant.

| Fichier | Contenu |
|---|---|
| `resources/scripts/submodule_common.py` | exécution de git, codes de sortie, validation des paramètres, environnement d'authentification, fichiers gérés |

Dans un dépôt qui utilise les skills, ce fichier est copié avec leurs scripts dans
`.github/submodule-sync/` : les workflows n'ont besoin d'aucun skill installé.

Rien ici ne s'adresse à Claude : il n'y a aucune instruction à suivre dans ce dossier.
