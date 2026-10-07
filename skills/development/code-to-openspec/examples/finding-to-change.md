# Exemple : d'un constat à un changement OpenSpec

Parcours complet sur un petit projet fictif (module de tarification). Les fichiers ci-dessous ont été produits puis contrôlés pour de vrai : `openspec validate fix-discount-rounding --strict` → valide (CLI 1.14.1) et `audit_tool.py check` → 0 erreur, 0 avertissement. Cela valide la **structure** ; le comportement n'est vérifié que par la reproduction (échec attendu avant correction). Le projet est générique ; il n'a rien de commun avec le dépôt qui héberge ce skill.

## 1. Demande

> « Analyse le calcul de remise du module `orders` et prépare les corrections avec OpenSpec. »

Mode : **analyse ciblée**. Pas de questionnaire préalable : le projet et le périmètre sont sans ambiguïté.

## 2. Preuves recueillies

- Comportement observé : `src/orders/pricing.py:3` appelle `round(subtotal_cents * rate)`. Pour 125 centimes à 10 %, `round(12.5)` vaut 12 en Python (arrondi au pair) ; `round(13.5)` vaut 14.
- Exigence documentée : `docs/pricing.md` : « une moitié (0,5 centime) est arrondie vers le haut ».
- Reproduction : `tests/test_f001_half_cent.py`, nouveau fichier, marqué `expectedFailure` avec la référence `F-001` (échec volontaire, signalé dans `state.md`).
- Autre observation, **non démontrée** : aucun contrôle du signe du taux → constat `F-002` *risque potentiel*, `expected_status: unknown`, question `D-001`. Elle n'entre dans aucune exigence.

## 3. Constat `F-001` (défaut confirmé)

`docs/audit/orders/findings/F-001-discount-half-cent-rounding.md`

```markdown
---
id: F-001
title: "La remise arrondit une moitié de centime vers le pair, pas vers le haut"
qualification: confirmed-defect
status: in-change
priority: P2
priority_rationale: "Écart d'un centime sur certaines remises ; parcours principal mais impact financier faible par commande"
evidence_level: executed
evidence:
  - src/orders/pricing.py:3
  - docs/pricing.md:5
  - "run: python -m unittest tests.test_f001_half_cent -> OK (expected failures=1) ; discount_cents(125, 0.10) renvoie 12"
current_behavior: "discount_cents(125, 0.10) renvoie 12 : round() arrondit 12,5 vers le pair"
expected_status: documented
expected: "Une moitié de centime est arrondie vers le haut : 13"
expected_source: "docs/pricing.md#arrondi"
cause_status: demonstrated
cause: "Utilisation de round() du langage, dont la règle est l'arrondi au pair"
impact: "Remises sous-évaluées d'un centime sur les moitiés exactes"
minimal_fix: "Arrondir par floor(x + 0.5) dans discount_cents"
acceptance:
  - "discount_cents(125, 0.10) == 13"
  - "la suite existante reste verte"
depends_on: []
open_questions: []
change: fix-discount-rounding
requirements:
  - Discount is rounded half up
scenarios:
  - Half cent rounds up
validated_by: ""
analyzed_commit: 5b4fe9e
---

## Historique

- 2026-10-07 — créé (commit `5b4fe9e`), reproduction en échec attendu.
```

## 4. Constat `F-002` (risque potentiel, resté hors changement)

```markdown
---
id: F-002
title: "Un taux de remise négatif n'est pas rejeté"
qualification: potential-risk
status: open
priority: P3
priority_rationale: "Aucun appelant observé ne passe un taux négatif ; effet : un total supérieur au sous-total"
evidence_level: local-read
evidence:
  - src/orders/pricing.py:1-3
current_behavior: "discount_cents ne contrôle pas le signe du taux"
expected_status: unknown
expected: ""
cause_status: unknown
impact: "Possible majoration silencieuse si un appelant futur passe un taux négatif"
minimal_fix: "A definir apres decision D-001"
acceptance:
  - "n/a avant décision"
depends_on: []
open_questions:
  - "D-001 : un taux négatif est-il une erreur, ou une majoration voulue ?"
change: ""
requirements: []
scenarios: []
validated_by: ""
analyzed_commit: 5b4fe9e
---
```

Un risque potentiel dont l'attendu est inconnu ne passe pas en `in-change` : `audit_tool.py check` le refuserait sans `validated_by`.

## 5. Changement `fix-discount-rounding`

Créé par `openspec new change "fix-discount-rounding"`, artefacts rédigés après `openspec instructions <artefact> --change fix-discount-rounding --json`.

### `proposal.md`

```markdown
# Proposal

## Why

La remise est arrondie par `round()` du langage, qui arrondit une moitié vers le pair le plus proche : 12,5 centimes donnent 12, 13,5 donnent 14. La documentation de tarification (`docs/pricing.md#arrondi`) demande qu'une moitié soit arrondie vers le haut. Constat traité : F-001 (`docs/audit/orders/findings/F-001-discount-half-cent-rounding.md`), reproduit par `tests/test_f001_half_cent.py`.

## What Changes

- Le calcul de la remise arrondit une moitié de centime vers le haut, comme le documente `docs/pricing.md`.
- Hors périmètre : l'arrondi du taux de TVA et l'affichage des montants (non examinés, voir `coverage.md`) ; toute décision sur les remises négatives (D-001, ouverte).

## Capabilities

### New Capabilities
- `discount-pricing`: calcul de la remise d'une commande et règle d'arrondi au centime.

### Modified Capabilities

## Impact

- Code : fonction de calcul de remise du module `orders` ; aucun changement d'API.
- Montants : les remises tombant exactement sur une moitié de centime augmentent d'un centime ; aucune migration de données (les remises déjà enregistrées ne sont pas recalculées).
```

### `specs/discount-pricing/spec.md`

Capacité nouvelle (aucune spec existante ne couvrait la remise), donc une section `## Purpose`. Chaque exigence décrit un comportement observable ; pas de nom de fonction ni de bibliothèque.

```markdown
# Spec Delta

## Purpose

Définit comment la remise d'une commande est calculée et arrondie au centime, afin que les totaux soient prévisibles et conformes à la documentation tarifaire.

## ADDED Requirements

### Requirement: Discount is rounded half up
Le système SHALL arrondir la remise au centime le plus proche, une moitié de centime étant arrondie vers le haut.

#### Scenario: Half cent rounds up
- **WHEN** le sous-total est de 125 centimes et le taux de remise de 10 %
- **THEN** la remise est de 13 centimes

#### Scenario: Below half cent rounds down
- **WHEN** le sous-total est de 124 centimes et le taux de remise de 10 %
- **THEN** la remise est de 12 centimes

#### Scenario: Exact amount is unchanged
- **WHEN** le sous-total est de 1000 centimes et le taux de remise de 10 %
- **THEN** la remise est de 100 centimes
```

### `design.md`

```markdown
# Design

## Context

Le calcul de remise est une fonction unique (`discount_cents`) utilisée par `order_total_cents`. Voir proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- Arrondi « moitié vers le haut » sur la remise, avec des tests qui figent la règle.

**Non-Goals:**
- Changer le type des montants ou introduire une bibliothèque décimale.
- Traiter les remises négatives (D-001).

## Decisions

- **Arrondi par arithmétique entière** plutôt que `Decimal` : le sous-total est en centimes entiers, le taux est un flottant ; l'arrondi `floor(x + 0.5)` suffit pour des valeurs positives. Alternative écartée : `Decimal` avec `ROUND_HALF_UP`, plus sûr face aux erreurs flottantes mais change les types exposés.

## Risks / Trade-offs

- [Un taux flottant peut produire 12,4999999…] → ajouter un test sur des taux usuels (5 %, 10 %, 15 %, 20 %) ; passer à `Decimal` si un cas échoue (nouveau constat).

## Validation

Le test de reproduction `tests/test_f001_half_cent.py` passe (retirer son marquage « échec attendu ») et la suite existante reste verte.
```

### `tasks.md`

Chaque tâche cite le constat, l'exigence et le scénario, et énonce sa vérification.

```markdown
# Tasks

## 1. Correction de l'arrondi

- [ ] 1.1 Arrondir la remise vers le haut sur une moitié (F-001 ; Requirement: Discount is rounded half up ; Scenario: Half cent rounds up) — vérifier : `python -m unittest discover -s tests -t .` passe et `tests/test_f001_half_cent.py` n'est plus marqué en échec attendu
- [ ] 1.2 Ajouter des tests pour les scénarios « Below half cent rounds down » et « Exact amount is unchanged » (F-001) — vérifier : les deux tests existent et passent
- [ ] 1.3 Ajouter un test sur les taux 5 %, 10 %, 15 % et 20 % pour des sous-totaux de 1 à 200 centimes (F-001, risque flottant du design) — vérifier : le test passe ; un échec ouvre un nouveau constat

## 2. Documentation

- [ ] 2.1 Citer la règle d'arrondi de remise dans `docs/pricing.md` avec un exemple chiffré (F-001) — vérifier : l'exemple du document est repris par un test
```

## 6. Contrôles

```text
$ openspec validate fix-discount-rounding --strict --json
→ "valid": true, "issues": []

$ python resources/audit_tool.py check --audit-dir docs/audit/orders
→ 2 constat(s) : confirmed-defect/in-change=1, potential-risk/open=1
→ 0 erreur(s), 0 avertissement(s).
```

La première ligne ne dit rien du comportement ; la seconde non plus. Le comportement sera vérifié quand le test de reproduction passera, après implémentation (non demandée ici : le skill s'arrête à la préparation).

## 7. Restitution (extrait)

> Mode : analyse ciblée, `orders/pricing`. Couverture : examiné `pricing.py` (tracé), non examiné TVA et affichage.
> Constats : 1 défaut confirmé P2 (F-001), 1 risque potentiel P3 (F-002).
> Changement créé : `openspec/changes/fix-discount-rounding/` (structure validée en mode strict).
> Exécuté : reproduction (échec attendu confirmé), `openspec validate --strict`, `audit_tool.py check`. Non exécuté : suite complète après correction (pas d'implémentation demandée).
> À clarifier : D-001, un taux négatif est-il une erreur ou une majoration voulue ?
