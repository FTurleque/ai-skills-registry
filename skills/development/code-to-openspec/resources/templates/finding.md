---
id: F-001
title: "Titre court, factuel, sans jugement"
qualification: confirmed-defect
status: open
priority: P2
priority_rationale: "Impact x probabilité x exposition, en une phrase"
evidence_level: traced
evidence:
  - src/chemin/relatif/fichier.ext:42-58
  - "run: <commande lancée> -> <résultat résumé>"
current_behavior: "Ce que le code fait, au présent, sans jugement (observé)"
expected_status: documented
expected: "Le comportement attendu"
expected_source: "docs/fichier.md#section"
cause_status: hypothesis
cause: "Cause démontrée, ou hypothèse (le dire)"
impact: "Conséquence concrète, pour qui, dans quel parcours"
minimal_fix: "La plus petite correction qui satisfait les critères"
acceptance:
  - "Critère vérifiable 1"
  - "Critère vérifiable 2"
depends_on: []
open_questions: []
change: ""
requirements: []
scenarios: []
validated_by: ""
resolved_by: ""
analyzed_commit: ""
---

<!--
Règles du front matter (contrôlées par resources/audit_tool.py) :
- Une valeur par ligne ; mettre entre guillemets toute valeur contenant « : ».
- qualification : confirmed-defect | potential-risk | proposed-improvement | decision-to-clarify
- status : open | in-change | resolved | rejected | stale
- priority : P0 | P1 | P2 | P3
- evidence_level : executed | traced | local-read | documentary
- expected_status : documented | proposed | unknown
- cause_status : demonstrated | hypothesis | unknown
- evidence : chemins RELATIFS à la racine du projet (chemin, chemin:ligne ou chemin:début-fin),
  ou "run: commande -> résultat" pour une exécution. L'entrée DOIT commencer exactement par « run: » ;
  y mettre le contexte dans le texte : "run: [avant correction, commit abc1234] commande -> résultat".
  Pas de chemin absolu, pas de secret.
- confirmed-defect exige evidence_level executed|traced, expected_status != unknown,
  et expected_source si documented. executed exige au moins une entrée "run:".
- status in-change exige change ; resolved exige change ou resolved_by (commit ou référence d'une correction faite hors changement OpenSpec) ; si expected_status n'est pas documented,
  validated_by (décision de l'utilisateur ou D-NNN) est aussi exigé.
- requirements / scenarios : noms EXACTS présents dans les deltas du changement.
- Ne jamais supprimer un constat : changer son statut et écrire l'Historique. Avant et après correction : deux entrées run:
  distinctes, dans l'ordre.
-->

## Contexte

Une à trois phrases : où, dans quel parcours, comment on y arrive.

## Sources contradictoires (si applicable)

| Source | Ce qu'elle dit | Référence |
|--------|----------------|-----------|
| Code | | `chemin:ligne` |
| Documentation | | `doc#section` |
| Test | | `chemin::nom` |

## Reproduction

Étapes minimales ou chemin du test de reproduction. Dire si le test est volontairement en échec.

## Historique

- AAAA-MM-JJ — créé (commit `<sha>`).
