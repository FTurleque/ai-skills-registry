---
name: Demande d'artefact
about: Proposer un artefact à ajouter au registre
title: "[ARTEFACT] "
labels: artifact-request
assignees: ''
---

## Type

Un seul. La règle est dans `docs/architecture.md` : le dossier dit le mécanisme, pas le sujet.

- [ ] **skill** — un fichier d'instructions que Claude charge quand la tâche s'y prête
- [ ] **plugin** — un paquet installable qui branche des composants sur Claude Code
- [ ] **sous-agent** — un assistant spécialisé, avec son contexte et ses outils
- [ ] **commande** — un raccourci `/nom`
- [ ] **hook** — du code exécuté sur un événement, sans être appelé
- [ ] **instructions** — un gabarit de contexte projet (`CLAUDE.md`, `AGENTS.md`)
- [ ] **serveur MCP** — une configuration de branchement d'outils externes
- [ ] **style de sortie** — une posture de réponse permanente

## Nom proposé

- **Nom** (kebab-case) : `mon-artefact`
- **Catégorie** : `development` / `documentation` / `refactoring` / `testing` / `analysis` / autre

## Ce qu'il fait

Et surtout : **quand** il doit s'appliquer. Pour une skill, un sous-agent ou une commande, c'est ce
qui décide du déclenchement.

## Surfaces visées

- [ ] `claude-code`
- [ ] `claude-desktop`
- [ ] `claude-ai`
- [ ] `claude-api`

## Cas d'usage réels

Décrire au moins une situation vécue où cet artefact aurait servi. Pas un cas hypothétique.

- Cas 1
- Cas 2

## Prérequis

Runtime, binaire, accès réseau, compte — tout ce qui doit être vrai pour que ça fonctionne.

## Pourquoi dans le registre

En quoi c'est réutilisable au-delà d'un seul projet. Un artefact utile une fois n'a pas sa place ici.

## Informations complémentaires

Références, outils existants qui s'en approchent, contraintes connues.
