# Modèle de preuve

Comment qualifier ce qu'on affirme. L'objectif : que le lecteur sache à tout moment ce qui est **démontré**, ce qui est **attendu et par qui**, et ce qui n'est qu'**opinion ou hypothèse**.

## Les sept qualifications

| Qualification | Définition | Preuve minimale | À ne pas faire |
|---------------|------------|-----------------|----------------|
| Comportement observé | Ce que le code fait ou ce qu'une exécution produit | `chemin:ligne`, ou sortie d'une commande (`run:`) | Y mêler un jugement (« à tort », « heureusement ») |
| Exigence documentée | Attendu écrit quelque part | Source citée précisément : document + section, ADR, spec OpenSpec, ticket, nom d'un test | Citer de mémoire ; prendre un commentaire de code périmé pour une exigence sans le dire |
| Exigence proposée | Comportement souhaité, à valider | Argumentaire et auteur de la proposition (ce skill, l'utilisateur) | L'écrire dans une spec comme un acquis |
| Défaut confirmé | Écart démontré entre observé et attendu | Reproduction exécutée, ou chaîne d'appels tracée de bout en bout, **et** attendu à source identifiée | Conclure à partir d'un seul fichier lu ; confirmer un écart par rapport à une exigence seulement proposée |
| Risque potentiel | Problème plausible non démontré | Indices + ce qu'il faudrait pour le démontrer | Le rédiger au présent (« le service plante ») |
| Amélioration proposée | Évolution argumentée | Bénéfice démontré ou chiffré ; coût évalué | La présenter comme une correction |
| Décision à clarifier | Information manquante qui empêche de trancher | Question, options, impact de chaque option, qui peut répondre | Choisir par défaut et continuer comme si c'était acquis |

## Niveau de preuve d'un constat

À renseigner dans `evidence_level` :

| Valeur | Sens |
|--------|------|
| `executed` | Une exécution (test, reproduction, commande) montre le comportement. La commande figure dans `evidence` sous la forme `run: <commande> -> <résultat>` |
| `traced` | Le parcours a été suivi de bout en bout dans le code (appelants, appelés, configuration), sans exécution |
| `local-read` | Une lecture locale suggère le comportement ; le contexte d'appel n'a pas été vérifié |
| `documentary` | Le constat repose sur des documents (contradiction entre sources), pas sur du code |

Un **défaut confirmé** exige `executed` ou `traced`. Un constat `local-read` est au mieux un risque potentiel.

`executed` qualifie la **preuve du comportement observé**, pas la gravité ni l'attendu : un risque potentiel peut être `executed` (on a exécuté `findQuery("x' OR '1'='1")` et obtenu la requête injectée) tout en restant un risque, parce que l'exploitation, l'exposition ou l'attendu ne sont pas démontrés.

## Contradictions entre sources

Quand code, tests, documentation, ADR ou specs divergent :

1. Les placer côte à côte dans le constat (tableau « Source — Ce qu'elle dit — Référence »).
2. Ne pas élire une source gagnante sans critère. Critères admissibles : une exigence validée par l'utilisateur dans la conversation (y compris quand sa demande prend explicitement parti : la citer dans `validated_by`) ; une spec OpenSpec archivée plus récente qu'un document ; un test qui passe contre un commentaire qui prétend le contraire (observation, pas intention).
3. Sinon : constat `decision-to-clarify`, avec la question à poser.
4. Une documentation périmée est un constat sur la documentation ; ce n'est pas, d'office, un défaut du code.

## Rédiger sans inventer

- Formulations sûres : « le code fait X (`chemin:ligne`) » ; « la documentation indique Y (`doc#section`) » ; « ces deux éléments se contredisent » ; « non démontré : il faudrait Z ».
- Formulations à proscrire : « l'auteur voulait », « le comportement prévu est » (sans source), « il est évident que », « comme d'habitude dans ce framework » (sans le vérifier), « tous les cas » (sans avoir tout examiné), « les tests passent » (sans les avoir lancés).
- Absence de preuve ≠ preuve d'absence. « Aucune validation trouvée dans les fichiers examinés » est correct ; « il n'y a pas de validation » ne l'est que si la chaîne complète (intergiciels, framework, appelants) a été vérifiée.
- Citer des chemins relatifs à la racine du projet ; jamais de chemin absolu propre à un poste.

## Spécification reconstruite depuis le code

Reconstruire ce qu'un module fait est utile. Cela produit une **description de l'existant** (`system-map.md`, tests de caractérisation), étiquetée comme telle. Elle ne devient une exigence que si l'utilisateur la valide, ou si une source documentée la confirme ; dans ce cas, la source ou la validation est citée dans le constat (`validated_by`). Voir `openspec-conversion.md` pour ce qui entre, ou non, dans une spec.

## Priorité

| Niveau | Repères |
|--------|---------|
| P0 | perte ou corruption de données, faille exploitable, indisponibilité du parcours principal |
| P1 | comportement faux sur un parcours principal, risque sérieux et plausible, blocage de livraison |
| P2 | comportement faux en situation limitée, dette qui ralentit nettement le travail |
| P3 | confort, cohérence, nettoyage |

La priorité combine impact, probabilité et exposition ; la justifier en une phrase (`priority_rationale`). Un risque potentiel peut être P1 s'il est lourd de conséquences, mais il reste un risque tant que non démontré.

## Refonte

Ne recommander une refonte architecturale que si : (a) plusieurs constats confirmés partagent une cause structurelle, (b) une correction locale a été examinée et écartée avec une raison, (c) un coût actuel est montré (incidents, lenteur de changement mesurée, impossibilité de tester). Sinon, proposer la plus petite correction qui satisfait les critères d'acceptation.
