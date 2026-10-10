# Articuler ADR, arc42 et OpenSpec

Aucune intégration native entre ces outils n'est supposée. Ce document décrit des conventions à appliquer à la main ; le projet peut en avoir d'autres, qui priment.

## arc42 : le dossier global, la section 9 comme index

arc42 reste la description d'ensemble. Sa section 9 sert d'**index** des décisions, pas de second registre :

```markdown
| Identifiant | Titre | Statut | ADR |
|---|---|---|---|
| ARCH-001 | Isolation du domaine | Acceptée | [ARCH-001](<chemin relatif vers l'ADR canonique>) |
```

L'index ne contient ni le contexte ni la décision. Si le dossier est exporté (HTML, DOCX), tout texte d'ADR inclus doit être généré depuis la source.

Lors d'un changement, n'examiner que les sections concernées :

| Impact du changement | Section arc42 |
|---|---|
| Frontières du système, interfaces externes | 3 — Contexte et périmètre |
| Stratégie générale | 4 — Stratégie de solution |
| Modules, responsabilités, dépendances | 5 — Vue des blocs |
| Scénarios et échanges à l'exécution | 6 — Vue d'exécution |
| Infrastructure, topologie | 7 — Vue de déploiement |
| Concept transversal (sécurité, persistance, erreurs…) | 8 — Concepts transversaux |
| Nouvelle décision, remplacement, changement de statut | 9 — Décisions : index et liens |
| Objectif ou scénario de qualité | 10 — Exigences de qualité |
| Écart accepté, risque, dette | 11 — Risques et dette technique |

Deux rappels :

- Une vue peut devoir changer **sans** nouvel ADR (un module ajouté dans le respect d'une décision existante modifie §5, rien d'autre).
- Toujours distinguer **architecture actuelle** et **architecture cible**. Une vue qui montre la cible le dit ; un écart connu entre les deux va en §11.

Diagrammes : Mermaid.

## OpenSpec : revue d'impact architectural

Le workflow OpenSpec du projet est conservé tel quel : ni réinitialisation, ni changement de schéma, ni migration des changements en cours. La revue d'impact est une **étape de lecture** ajoutée à la conception ; elle s'écrit dans l'artefact de conception existant (`design.md` dans le schéma `spec-driven`) ou, à défaut, dans la proposition.

Elle se conclut par une seule ligne parmi quatre :

| Conclusion | Ce qu'on écrit dans l'artefact |
|---|---|
| Aucun nouvel ADR nécessaire | la phrase, et une ligne de justification |
| ADR existant applicable | l'identifiant et le lien, plus l'effet sur ce changement |
| Clarification nécessaire | l'identifiant, ce qui manque ; la clarification se fait dans l'ADR |
| Nouvelle décision ou remplacement à proposer | le lien vers le brouillon ; l'implémentation qui en dépend attend l'acceptation |

Exemple de bloc, à adapter :

```markdown
## Impact architectural

- Conclusion : ADR existant applicable.
- Décisions : [ARCH-001](<lien>) — le nouvel adaptateur dépend du domaine, pas l'inverse.
- Vues arc42 à mettre à jour : §5 (nouveau bloc). Aucune autre.
- Contrôles : `<commande du projet>` ; revue humaine pour <aspect non automatisé>.
```

Les artefacts OpenSpec **référencent** les ADR et les vues ; ils ne les recopient pas.

Un schéma OpenSpec n'est modifié que si le bénéfice est démontré, localement au projet, de façon versionnée et compatible avec les changements en cours. Un schéma qui imposerait un ADR par changement contredit la politique : il faut pouvoir conclure « aucun nouvel ADR nécessaire ».

## Avant d'archiver un changement

| Vérification | Preuve attendue |
|---|---|
| Le code livré respecte les ADR cités | résultats des contrôles, avec leur couverture réelle |
| Les ADR proposés par le changement ont un statut tranché | accepté par une personne, ou retiré du changement |
| Les vues arc42 annoncées sont à jour | diff des sections concernées |
| L'index §9 reflète les statuts | `adr_tool.py check`, ou lecture |
| Les liens survivent à l'archivage | les ADR ne vivent pas dans le dossier du changement ; liens relatifs revérifiés |
| Actuel et cible ne sont pas confondus | écarts restants consignés en §11 ou dans un suivi |

Un point non vérifié s'écrit « non vérifié », avec la raison.
