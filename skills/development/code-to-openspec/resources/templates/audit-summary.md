# Synthèse d'audit — <périmètre>

- **Mode** : global | ciblé | reprise
- **Commit analysé** : `<sha>` (arbre : propre | modifié par l'utilisateur)
- **Date** : AAAA-MM-JJ

## En bref

Trois à cinq phrases : ce qui a été examiné, ce qui ressort, ce qui reste incertain.

## Couverture

Examiné / partiel / non examiné — voir `coverage.md`. Dire clairement ce qui n'a pas été vu.

## Constats

| Qualification | P0 | P1 | P2 | P3 |
|---------------|---:|---:|---:|---:|
| Défaut confirmé | | | | |
| Risque potentiel | | | | |
| Amélioration proposée | | | | |
| Décision à clarifier | | | | |

Constats saillants : `F-NNN` titre (une ligne chacun).

## Changements OpenSpec

| Changement | Constats | Statut (planifié / créé / structure validée) |
|------------|----------|-----------------------------------------------|

## Vérifications

| Contrôle | Exécuté ? | Résultat |
|----------|-----------|----------|
| Suite de tests existante | oui / non | |
| Test de reproduction | oui / non | |
| `openspec validate --strict` | oui / non | |
| `audit_tool.py check` | oui / non | |

La validation de structure OpenSpec ne vaut pas validation du comportement.

## Décisions à clarifier

Renvoi à `decisions.md` : D-NNN, question, qui peut répondre.

## Limites

Environnement, outils absents, périmètre, hypothèses.
