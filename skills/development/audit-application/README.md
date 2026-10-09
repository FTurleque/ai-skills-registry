# Audit d'application

> Audit technique complet d'une base de code : rapport versionné dans le dépôt, corrections découpées en sprints ordonnés par dépendance, et tableau de bord de synthèse.

## Ce que ça change

Sans le skill, « audite cette app » produit une liste de remarques sans ordre d'exécution, dont une partie n'est pas vérifiable parce que son prérequis n'est pas livré. Avec lui :

- six axes audités en parallèle (architecture, qualité, sécurité, tests, performance, dépendances et exploitation), un sous-agent par axe ;
- aucun constat sans preuve `fichier:ligne` ou commande exécutée ; ce qui n'a pas pu être vérifié va dans les angles morts ;
- une note par axe dont le calcul est documenté, et 3 à 5 thèmes transverses qui expliquent la majorité des constats ;
- un découpage en sprints dont l'ordre est **vérifié par script** (aucun prérequis dans un sprint postérieur), avec chemin critique, charge en fourchette et critère de sortie vérifiable par sprint ;
- un rapport sous `docs/audit/<AAAA-MM-JJ>/` et un artefact HTML autonome (notes, diagramme d'architecture, répartition, feuille de route, tableau filtrable) ;
- aucune modification du code applicatif pendant l'audit.

Trois profils : *complet* (défaut), *sécurité* (axes 3 et 6 en profondeur), *rapide* (axes 1 à 3 sur le cœur du dépôt).

## Installation

| Surface | Emplacement |
|---------|-------------|
| Claude Code | `~/.claude/skills/audit-application/` ou `<projet>/.claude/skills/audit-application/` |
| Application de bureau | mêmes emplacements dans l'onglet Code ; mode Cowork : réglages de l'application ou plugin |

```bash
cp -r skills/development/audit-application ~/.claude/skills/
```

Sous Windows, `~` est `%USERPROFILE%`. Voir [docs/install.md](../../../docs/install.md) pour le détail par surface.

Prérequis facultatif : `git` (fréquence de modification des fichiers, utilisée pour hiérarchiser les modules).

## Usage

Demander en langage naturel (voir [examples/invocations.md](examples/invocations.md)) :

> Audite cette application.
> Fais un audit de sécurité du dépôt.
> Revue technique complète, avec un découpage en sprints.

Le skill cadre d'abord le périmètre (stack, carte du dépôt, modules critiques), annonce les axes retenus, puis lance la collecte.

## Limites

- **Pas d'indexation de code.** L'audit repose sur la lecture directe (`Glob`, `Grep`, `Read`), sans graphe d'appels : le skill interdit explicitement les serveurs d'indexation tiers (sauf demande de l'utilisateur) et liste ce manque dans les angles morts. Le code atteint seulement par réflexion ou injection de dépendances est mal couvert.
- **Couverture bornée.** Au-delà de ~2 000 fichiers, l'audit s'en tient au cœur identifié en phase 0 ; les modules secondaires sont survolés.
- **Rien n'est observé à l'exécution.** Les constats de performance et de sécurité sont lus dans le code, pas mesurés ni exploités.
- **Les notes sont un barème, pas une mesure.** Une densité de constats structurels peut dégrader une note sans que rien ait été mesuré ; le skill demande de le dire avant de citer la note.
- **Dépend de capacités propres à Claude.** Sous-agents (`Agent`), publication d'artefact, et skills compagnons `artifact-design`, `dataviz` et `artifact-diagramming` pour la synthèse. Sans elles, le rapport dans le dépôt reste produit mais pas le tableau de bord. Pas de sens sur claude.ai ou l'API sans accès aux fichiers du dépôt : seules les surfaces `claude-code` et `claude-desktop` sont déclarées.
- **Dépendances externes facultatives.** Les audits de dépendances (`npm audit`, `pip-audit`, `cargo audit`…) ne sont lancés que s'ils sont déjà installés ; sinon le manque devient une recommandation.
- **Front matter du registre.** `SKILL.md` porte des champs propres au registre (`kind`, `displayName`, `tags`, `status`…) en plus de `name` et `description`. Claude Code les tolère ; un outil de téléversement plus strict pourrait les refuser (non vérifié) — ne garder alors que `name`, `description` et `license`.
- **Statut `experimental`.** Le skill n'a pas été rejoué dans le cadre de ce dépôt pour établir la liste des surfaces ; les déclarations de compatibilité sont à confirmer à l'usage.
