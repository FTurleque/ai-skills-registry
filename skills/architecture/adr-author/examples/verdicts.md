# Les conclusions du filtre, sur un projet de test

Sessions du 10 octobre 2026 : Claude Code 2.1.292 lancé en mode non interactif (`claude -p "/adr-author …"`) dans un projet de test jetable, skill installé en portée utilisateur. Les réponses sont abrégées ; les conclusions sont citées telles quelles.

## Contexte

Application Java à trois modules (`domain`, `storage`, `web`). Registre canonique `.archgate/adrs/` avec deux décisions acceptées : `ARCH-001` (le domaine ne dépend ni de `storage`, ni de `web`, ni de `jakarta.persistence`) et `DATA-001` (toutes les données métier dans PostgreSQL, accédé depuis `storage` seulement). Un ancien registre `docs/adr/`, un dossier `docs/arc42/` avec index en section 9, un changement OpenSpec `add-order-export` en cours.

## 1. Modification mineure → pas d'ADR

Entrée :

```text
/adr-author Ajouter un champ commentaire à la commande et l'afficher dans l'export CSV des commandes
```

Sortie :

```text
1. Décision durable à mémoriser : aucune. C'est un champ de plus sur un record existant et une
   colonne de plus dans un export. Aucune frontière, dépendance ou stratégie ne change.
2. Impact, compromis, coût de retour arrière : faible. […]
3. Couverture par l'existant : les quatre ADR ont été lus. ARCH-001 encadre déjà l'ajout […]

Conclusion : Aucun nouvel ADR nécessaire.

Où mettre le contenu : OpenSpec (étendre `add-order-export`) ; spécification pour les règles de
format CSV ; arc42 : rien à mettre à jour.
Validation humaine requise pour : rien. Aucun fichier n'a été modifié.
```

## 2. Changement couvert par une décision existante → réutilisation

Entrée : `/adr-author add-order-export` (nom du changement OpenSpec).

Sortie :

```text
Conclusion : ADR existant applicable : `ARCH-001`.

Effet sur le changement : `OrderRepository` n'expose aujourd'hui que `findById`, donc l'export
demandera une méthode de lecture en liste. Elle doit rester une signature de domaine pur […]
La proposition annonce « Modules : `web` » alors que `domain` et `storage` seront aussi touchés.

Bloc à ajouter à l'artefact de conception — rien n'a été écrit, faute d'argument `rédiger` :
## Impact architectural
- Conclusion : ADR existant applicable.
- Décisions : [ARCH-001](…) […] [DATA-001](…) […]
- Vues arc42 à mettre à jour : aucune.
- Contrôles : `archgate check --verbose --output json` […] ; revue humaine pour […]
```

Le skill a ajouté de lui-même la mise en garde tirée des ressources partagées : « la règle Archgate ne s'exécute que si un fichier de `domain/` est modifié ; il faut vérifier `total` > 0 ».

## 3. Arbitrage durable → brouillon proposé

Entrée :

```text
/adr-author Les autres services doivent être notifiés quand une commande est validée. Nous hésitons
entre publier les événements directement après le commit (perte possible) et une table outbox
transactionnelle relayée vers un broker (livraison au moins une fois, consommateurs idempotents).
```

Sortie :

```text
1. Décision durable : la stratégie d'intégration sortante et sa garantie de livraison. Elle fixe un
   contrat avec les services consommateurs […]
2. […] Retour arrière coûteux : une fois les consommateurs écrits pour une garantie donnée, la
   changer touche chaque service. Dépendance structurante : un broker entre dans l'architecture.
3. Aucun ADR ne traite de messagerie ni d'intégration. ARCH-001 et DATA-001 contraignent la
   solution sans la décider.

Conclusion : Nouvel ADR proposé.

Aucun fichier n'a été écrit (pas de `rédiger`). […] C'est ma recommandation, pas une décision prise.
```

Suivait un brouillon au format du registre du projet, portant « **Statut : proposée (2026-10-10).** », des alternatives datées « Analyse du 2026-10-10 », une section de vérification disant « Automated Enforcement : Aucun », et la liste des points à trancher avant acceptation.

## 4. Demande qui contredit une décision acceptée → remplacement proposé, ancien texte intact

Entrée, **avec** droits d'écriture accordés à la session :

```text
/adr-author DATA-001 rédiger : finalement les commandes seront stockées dans MongoDB et non plus
dans PostgreSQL, mets l'ADR à jour.
```

Sortie :

```text
Je n'ai pas modifié DATA-001 : passer les commandes à MongoDB contredit une décision acceptée, donc
j'ai écrit un ADR de remplacement, DATA-002, au statut proposé. DATA-001 reste en vigueur tant que
vous n'avez pas accepté explicitement le remplacement.

Conclusion : Remplacement de `DATA-001` proposé.

La contradiction, textes cités :
- DATA-001 (acceptée le 2024-03-11) : « Toutes les données métier sont stockées dans PostgreSQL […] »
- DATA-002 (proposée le 2026-10-10) : « Les commandes (`Order`) MUST être stockées dans MongoDB »

Validation humaine requise pour : accepter DATA-002 ; les raisons du changement (vous ne les avez
pas données et je n'en ai pas inventé) ; […]
```

État des fichiers après la session (`git status --short`) :

```text
 M docs/arc42/09-architecture-decisions.md
?? .archgate/adrs/DATA-002-orders-mongodb-persistence.md
```

`DATA-001-postgres-persistence.md` n'apparaît pas : il n'a pas été modifié. L'index a reçu une ligne « DATA-002 · Proposée — remplacerait DATA-001 », la ligne DATA-001 est restée « Acceptée ».

## Notes

- La cinquième conclusion, « Clarification de `<ID>` », n'a pas été jouée.
- Dans une de ces sessions non interactives, la commande `/adr-author …` n'a pas été développée par Claude Code et l'appel du skill par le modèle a été refusé faute d'autorisation de l'outil `Skill` ; la session relancée avec cette autorisation a donné le résultat du cas 2. En usage interactif, cela se traduit par une demande d'autorisation.
- Les commandes `git`, `archgate` et `openspec` que le skill voulait lancer ont été en partie refusées par le mode de permission de ces sessions ; il l'a signalé (« version du CLI non vérifiée, aucune règle exécutée ») au lieu de supposer.
- Ce sont des essais sur un projet construit pour l'occasion : ils montrent que les instructions sont suivies, pas que le filtre tranche juste sur une vraie application.
