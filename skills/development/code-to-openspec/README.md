# Code to OpenSpec

> Retrouve ce qu'une application fait à partir de son code, sépare les preuves des intentions, puis prépare des changements OpenSpec traçables.

## Ce que ça change

Sans le skill, « analyse l'application et prépare les corrections » produit vite une liste de défauts mélangeant faits, opinions et hypothèses, avec une spécification qui n'est que le code reformulé. Avec lui :

- chaque affirmation porte une qualification (comportement observé, exigence documentée ou proposée, défaut confirmé, risque potentiel, amélioration proposée, décision à clarifier) ;
- le code actuel n'est jamais pris pour la spécification souhaitée, les contradictions entre code, tests, documentation et ADR sont montrées côte à côte ;
- le travail suit une chaîne vérifiable : **constat → changement → exigence → scénario → tâche → validation** ;
- par défaut, rien n'est modifié dans le code de production, aucun commit n'est créé, le travail non commité de l'utilisateur est préservé ;
- une analyse peut être reprise sans recréer les constats ni écraser les décisions.

Trois modes, choisis d'après la demande : audit global, analyse ciblée, reprise d'un travail existant.

Le skill est indépendant du langage, du framework, de l'IDE et de l'OS. Le MCP d'un IDE (JetBrains par exemple) est utilisé s'il est disponible, jamais exigé.

## Installation

| Surface | Emplacement | Vérifié |
|---------|-------------|---------|
| Claude Code, portée utilisateur | `~/.claude/skills/code-to-openspec/` | oui (convention documentée par Claude Code ; skill exercé en simulation, voir Limites) |
| Claude Code, portée projet | `<projet>/.claude/skills/code-to-openspec/` | oui (même convention) |
| Application de bureau | réglages de l'application, ou via un plugin | non vérifié |

```bash
cp -r skills/development/code-to-openspec ~/.claude/skills/
```

Copier le dossier **entier** : `SKILL.md` renvoie à `resources/`. Sous Windows, `~` est `%USERPROFILE%`.

Prérequis facultatifs : `git` (état du dépôt, dérive), CLI `openspec` 1.x (création et validation des changements ; **non installé ni initialisé par le skill**), Python 3.8+ (`resources/audit_tool.py`). Sans eux le skill fonctionne : il prépare des brouillons au format OpenSpec dans le dossier d'audit et indique ce qui reste à faire.

## Usage

Demander en langage naturel (voir [examples/invocations.md](examples/invocations.md)) :

> Analyse cette application et prépare les corrections avec OpenSpec.
> Retrouve les spécifications de la fonctionnalité d'export à partir du code.
> Compare le code aux spécifications existantes.

Livrables, dans le dossier d'audit du projet (`docs/audit/<périmètre>/` à défaut de convention existante) : synthèse, cartographie, `findings/F-NNN-*.md`, plan de correction, `decisions.md`, `coverage.md`, `state.md` ; changements dans `openspec/changes/`. Parcours complet illustré dans [examples/finding-to-change.md](examples/finding-to-change.md).

## Contenu

| Fichier | Rôle |
|---------|------|
| `SKILL.md` | règles, modes, déroulé (court, chargé au déclenchement) |
| `resources/workflow.md` | découverte, modes, couverture, lots, reprise |
| `resources/evidence-model.md` | qualifications, niveaux de preuve, contradictions |
| `resources/analysis-axes.md` | axes d'investigation, diagrammes Mermaid, C4, arc42 |
| `resources/openspec-conversion.md` | constats → changements, formats vérifiés, traçabilité, OpenSpec absent |
| `resources/execution-safety.md` | garde-fous, arbre sale, contenu hostile, implémentation sur demande |
| `resources/validation-checklist.md` | grille de validation du travail |
| `resources/templates/` | constat, état, couverture, cartographie, synthèse, décisions, plan |
| `resources/audit_tool.py` | `check`, `snapshot`, `drift`, `next-id` : contrôles déterministes (facultatif) |
| `resources/tests/test_audit_tool.py` | 32 tests du script (`python -m unittest discover -s resources/tests`) |
| `examples/` | invocations, parcours constat → changement, scénarios de validation |

## Limites

- **Formats OpenSpec vérifiés avec le CLI 1.14.1** (schéma `spec-driven`). Une autre version ou un autre schéma peut différer : le skill demande de suivre `openspec instructions`, qui fait foi ; les gabarits du skill ne sont qu'un repli.
- **Le skill ne prouve pas le comportement.** La validation de structure d'OpenSpec (`openspec validate`) et le script d'audit vérifient des formes et des liens, pas la justesse des constats. Un constat faux et bien formé passe les contrôles.
- **Le contrôle de doublons est une aide.** `audit_tool.py check` avertit quand deux constats citent la même preuve `fichier:lignes` ; deux constats distincts sur un même passage sont parfois légitimes (changer les lignes citées, ou ignorer l'avertissement et le dire).
- **Qualité d'analyse limitée par la couverture.** Sur un grand dépôt, une passe ne voit pas tout ; le registre de couverture dit ce qui manque, il ne le comble pas.
- **Aucune exécution possible sans environnement.** Si le build est bloqué (outil, réseau, secret), les constats restent `traced` ou `local-read`, jamais `executed`.
- **Pas d'usage sur claude.ai ni via l'API sans accès au dépôt** : le skill suppose l'accès aux fichiers du projet ; `audit_tool.py` suppose un interpréteur Python. Seules les surfaces `claude-code` et `claude-desktop` sont déclarées.
- **Front matter du registre** : `SKILL.md` porte des champs propres au registre (`kind`, `displayName`, `tags`, `status`…) en plus de `name` et `description`. Claude Code les tolère ; un autre outil de téléversement plus strict que la spécification Agent Skills pourrait les refuser (non vérifié) — retirer alors ces champs en ne gardant que `name`, `description` et `license`.
- **`audit_tool.py` n'a été testé qu'avec Python 3.13** ; la compatibilité 3.8+ est visée (bibliothèque standard, pas de syntaxe récente) mais non vérifiée.
- **Validation par simulation** : le skill a été exercé par des agents suivant ses instructions sur des projets de test, pas sur de grands projets réels. Résultats et ce qui reste proposé : [examples/validation-scenarios.md](examples/validation-scenarios.md).
