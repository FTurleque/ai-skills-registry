# Convertir les constats en changements OpenSpec

Formats vérifiés avec le CLI OpenSpec **1.14.1**, schéma `spec-driven` (`proposal → specs → design → tasks`). Le CLI fait foi : avant d'écrire chaque artefact, lancer `openspec instructions <artefact> --change <nom> --json` et suivre `instruction`, `template`, `context` et `rules` (contraintes pour l'agent : ne pas les recopier dans le fichier). Version ou schéma différents : suivre le CLI.

## 1. Quels constats deviennent des changements

| Constat | Traitement |
|---------|------------|
| Défaut confirmé, attendu **documenté** | Candidat direct à un changement (correction) |
| Défaut confirmé, attendu seulement **proposé** | Ne pas traiter comme acquis : décision à clarifier d'abord (`decisions.md`) |
| Amélioration proposée | Changement seulement si l'utilisateur l'a retenue (`validated_by`) ; sinon plan de correction |
| Risque potentiel | Pas d'exigence. Tâche d'investigation ou de test de caractérisation dans un changement existant, ou ligne du plan |
| Décision à clarifier | `decisions.md` ; le changement concerné reste en attente ou ne contient que ce qui ne dépend pas de la réponse |
| Contradiction doc/code | Décision à clarifier ; puis soit correction du code, soit correction de la doc (changement `skip_specs` si aucun comportement spécifié ne change) |

Une exigence incertaine n'entre **jamais** dans un delta de spec comme décision acquise. Si le comportement attendu est incertain mais l'investigation utile, la tâche est « lever D-NNN » (vérification : la réponse est consignée dans `decisions.md`), pas une exigence `SHALL`.

Précisions :

- **Aucun constat convertible** (aucun attendu documenté ni validé) : le dire dans la restitution. Ne créer aucun changement ; au plus un brouillon conditionnel dans le dossier d'audit, avec des tâches « lever D-NNN ».
- **Une demande générale n'est pas une validation.** « Prépare les corrections » ne valide ni une amélioration proposée ni un attendu incertain. En revanche, si l'utilisateur prend explicitement parti dans sa demande (« la doc a raison, le code est faux »), c'est une validation : la citer dans `validated_by` (« demande de l'utilisateur, <date> »).
- **Attendu documenté mais mécanisme non documenté** (le README dit « refusé » sans dire comment) : seule la partie observable documentée entre dans le delta ; le mécanisme (exception, code d'erreur, journalisation) devient une décision. Ne pas déduire par négation ce que le texte ne dit pas ; un scénario déduit est signalé comme tel dans le constat.
- **Défaut dont la correction dépend d'une décision** : si la réponse peut changer les specs, ne pas créer le changement (brouillon seulement) ; si elle ne touche que le mécanisme, créer le changement avec « lever D-NNN » en première tâche.

## 2. Regrouper en changements limités

- Un changement = une cause racine, une capacité ou un parcours ; relisible d'une traite (ordre de grandeur : quelques groupes de tâches, pas dix).
- Ne pas mêler refactoring et changement de comportement dans un même changement.
- Dépendances entre changements : les écrire dans `Impact` de la proposition et dans `depends_on` des constats.
- Audit global : créer d'abord les changements des constats confirmés les plus prioritaires (quelques-uns par passe) ; lister les autres groupes dans `remediation-plan.md`.
- Nom du changement : kebab-case, décrit le résultat (`fix-discount-rounding`). Un changement du même nom existe déjà : demander s'il faut le continuer ou en créer un autre ; en reprise de **son propre** travail, le continuer.

## 3. Procédure

1. **Contexte** : `openspec context --json` (racine faisant foi), lire `openspec/config.yaml` (`context`, `rules`, langue). Racine absente : voir section 7.
2. **Réutiliser l'existant** : `openspec list --specs` (inventaire), `openspec show <spec> --type spec --json --no-scenarios` pour un aperçu, puis lecture complète `openspec show <spec> --type spec`. Réutiliser le chemin exact d'une capacité existante ; ne pas créer de quasi-doublon. `openspec list` sans `--specs` liste les changements en cours : vérifier qu'aucun ne couvre déjà le constat.
3. **Créer** : `openspec new change "<nom>"` (jamais si la racine est absente). Puis `openspec status --change "<nom>" --json` pour l'ordre des artefacts.
4. **Écrire chaque artefact** dans l'ordre des dépendances, après lecture de `openspec instructions`. Relire depuis le disque les artefacts dont on dépend. Dans `spec-driven`, `status` garde `tasks` bloqué tant que `specs` **et** `design` n'existent pas : écrire un `design.md` court (même pour un bug simple), ou, si son `instruction` le déclare facultatif et qu'aucun critère d'inclusion ne s'applique, le sauter explicitement et écrire `tasks.md` quand même (une dépendance habilite, elle ne bloque pas).
   - **Capacité existante muette sur le point traité** : ajouter l'exigence en `ADDED` dans la capacité existante (même chemin sous `specs/`, sans `## Purpose`). `MODIFIED` seulement si une exigence existante change de comportement.
   - **Tâches d'implémentation** : elles peuvent légitimement modifier ou retirer des tests (par exemple le marquage « échec attendu » d'un test de reproduction). L'interdiction de modifier les tests existants vaut pour l'analyse, pas pour l'application d'un changement.
   - Ne pas recopier dans les artefacts du projet analysé des commandes qui pointent vers ce skill (`audit_tool.py`).
5. **Contrôler** : section 6.

## 4. Correspondance constat → artefacts (schéma `spec-driven`)

| Contenu du constat | Où il va |
|--------------------|----------|
| Problème et preuves | `proposal.md` › **Why** : résumé et renvoi `F-NNN` (+ chemin du fichier de constat) ; ne pas recopier le constat |
| Objectif, ce qui change, ruptures | `proposal.md` › **What Changes** (marquer **BREAKING** si besoin) |
| Périmètre et exclusions | `proposal.md` › **What Changes** et **Impact** ; exclusions explicites. `design.md` › **Non-Goals** pour les limites de conception |
| Capacités touchées | `proposal.md` › **Capabilities** (nouvelles / modifiées) |
| Exigences attendues | `specs/<capacité>/spec.md` : `ADDED` / `MODIFIED` / `REMOVED` / `RENAMED` |
| Scénarios d'acceptation | `#### Scenario:` sous chaque exigence |
| Conception, alternatives | `design.md` › **Decisions** (avec alternatives écartées) |
| Compatibilité, migration, risques | `design.md` › **Risks / Trade-offs** et **Migration Plan** (créer `design.md` dès qu'il y a migration, donnée, sécurité, performance ou plusieurs modules) |
| Stratégie de validation | `tasks.md` (la vérification est dans chaque tâche) et, si utile, une section **Validation** de `design.md` |
| Tâches | `tasks.md` |
| Questions ouvertes | `design.md` › Open Questions **seulement** si la réponse ne change ni specs, ni approche, ni tâches ; sinon `decisions.md` et question à l'utilisateur |

## 5. Formats d'artefact (rappel vérifié)

Titres et mots-clés structurels restent en anglais (`### Requirement:`, `#### Scenario:`, `WHEN`/`THEN`, `SHALL`/`MUST`) ; le contenu suit la langue de `openspec/config.yaml` ou celle du projet.

**Delta de spec** (`specs/<capacité>/spec.md`) :

```markdown
# Spec Delta

## Purpose
<!-- Capacité NOUVELLE seulement : 50 caractères ou plus. Supprimer pour une capacité existante. -->

## ADDED Requirements

### Requirement: <nom>
Le système SHALL <comportement observable>.

#### Scenario: <nom>
- **WHEN** <condition>
- **THEN** <résultat attendu>

## MODIFIED Requirements
<!-- Copier le bloc COMPLET de l'exigence existante (titre + tous ses scénarios), puis le modifier. -->

## REMOVED Requirements

### Requirement: <nom>
**Reason**: <pourquoi>
**Migration**: <comment faire autrement>
```

Règles de contrôle : exactement **quatre** `#` pour un scénario (trois ou des puces échouent sans bruit) ; chaque exigence a au moins un scénario ; description d'exigence ≤ 500 caractères (au-delà : avertissement, et échec en mode strict) ; un comportement par exigence ; `SHALL`/`MUST` pour le normatif ; pas de nom de classe, de bibliothèque ni de détail d'implémentation dans une spec ; `MODIFIED` incomplet perd du contenu à l'archivage (pour ajouter sans changer l'existant, utiliser `ADDED`) ; chemin de capacité modifiée = chemin exact sous `openspec/specs/`.

**Aucun changement de comportement spécifié** (refactoring pur, tests, documentation) : poser `skip_specs: true` dans le `.openspec.yaml` du changement au lieu d'inventer une exigence ; `openspec validate` rejette un changement sans delta sans ce marqueur.

**`tasks.md`** : cases `- [ ] X.Y description`, groupes `## N.`, ordre par dépendance, **vérification énoncée dans chaque tâche**, tests et documentation livrés dans le groupe qui les appelle (pas de groupe final « tests »). Pas de `- [~]` ni `- []` (comptés non faits). Exemple d'ancrage de traçabilité :

```markdown
- [ ] 1.2 Corriger l'arrondi du total (F-004 ; Requirement: Rounded order total ; Scenario: Half-cent rounds up) — vérifier : le test `F-004` passe et le scénario est couvert
```

## 6. Traçabilité

Chaîne : **Constat → changement → exigence → scénario → tâche → validation.**

| Maillon | Où il est écrit |
|---------|-----------------|
| Constat → changement | front matter du constat : `change: <nom>`, statut `in-change` ; `proposal.md` › Why cite `F-NNN` |
| Changement → exigence → scénario | front matter du constat : `requirements:` et `scenarios:` (noms exacts) ; ces noms existent dans les deltas |
| Tâche | la ligne de `tasks.md` cite `F-NNN`, l'exigence et le scénario visés |
| Validation | la tâche énonce sa vérification ; le constat consigne `run:` avant et après correction |

Contrôle automatisable : `python <dossier-du-skill>/resources/audit_tool.py check --audit-dir <dossier> [--openspec-root openspec]` vérifie que le changement existe, que `tasks.md` cite le constat, que les exigences et scénarios nommés existent, qu'un constat non démontré ou non validé n'est pas passé en `in-change`. Le champ `change:` accepte le nom d'un brouillon de `changes-draft/` : le contrôle le cherche aussi là. Sans Python : faire ces vérifications à la main avec `openspec show` et une recherche textuelle.

## 7. Valider

Deux validations distinctes, à rapporter séparément :

1. **Structure OpenSpec** : `openspec validate <nom> --strict --json` (ou `--changes`). Vérifie la forme (deltas, scénarios, longueurs, `Purpose`). Ne dit **rien** du comportement logiciel. Corriger les erreurs ; un avertissement strict non corrigé est signalé.
2. **Comportement réel** : tests lancés, reproduction, relecture du parcours. Avant implémentation : l'état « défaut reproduit » ; après implémentation (si demandée) : « reproduction passée + suite existante ». Sans exécution, écrire « non vérifié ».

## 8. OpenSpec absent ou inutilisable

| Situation | Conduite |
|-----------|----------|
| `openspec list --json` donne `"root": null`, ou pas de dossier `openspec/` | Poursuivre l'analyse. Préparer des **brouillons** dans le dossier d'audit : `changes-draft/<nom>/{proposal.md,design.md,tasks.md,specs/<capacité>/spec.md}` au format ci-dessus (plus `.openspec.yaml` avec `skip_specs: true` si aucun comportement spécifié ne change). Expliquer : `openspec init` (à lancer par l'utilisateur ou sur sa demande), puis déplacer les brouillons et relancer `openspec instructions` / `openspec validate`. Ne pas lancer `init` dans le projet, ne pas créer `openspec/` à la main |
| CLI présent, racine absente, brouillons à valider | Autorisé : créer un **dossier temporaire hors du projet**, y lancer `openspec init --tools none`, `openspec new change <nom>`, copier les brouillons dans `openspec/changes/<nom>/`, puis `openspec instructions <artefact> --change <nom> --json` (gabarits du schéma réellement installé) et `openspec validate <nom> --strict`. Supprimer le dossier ensuite. Rien n'est écrit dans le projet analysé ; dire que la validation a eu lieu sur une copie |
| CLI absent, dossier `openspec/` présent | Lire et écrire les fichiers selon la structure existante ; dire que `validate` n'a pas été exécuté |
| Ni l'un ni l'autre, et l'utilisateur ne veut pas d'OpenSpec | Livrer constats et plan ; ne rien produire au format OpenSpec |
| Magasin (`store`) déclaré ou nommé | `openspec store list --json`, puis `--store <id>` sur les commandes qui l'acceptent, de façon constante |
| Installer le CLI | Ne pas le faire. Indiquer la procédure officielle (documentation du projet OpenSpec) et laisser l'utilisateur la lancer |
