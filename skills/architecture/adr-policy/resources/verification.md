# Rendre une décision vérifiable, et dire ce qui l'a été

## Ce que chaque ADR précise

| Rubrique | Contenu |
|---|---|
| Périmètre | modules, dossiers ou motifs de fichiers concernés — **tous**, pas seulement le module en cours |
| Contraintes concrètes | ce qui est interdit ou exigé, formulé de façon observable |
| Contrôles automatisés | la règle ou le test qui existe **réellement**, avec son chemin |
| Commande | celle qu'on tape, dans le build existant du projet |
| Revue humaine | ce qu'aucun contrôle ne couvre, et qui le regarde |

Un ADR purement textuel n'est pas « automatiquement vérifiable ». Un ADR non automatisable reste légitime si son mode de revue est écrit.

## Choisir le contrôle

| Contrainte | Outil adapté |
|---|---|
| Dépendances entre couches, cycles, règles de nommage structurelles en Java | test ArchUnit, dans le build Maven ou Gradle |
| Présence, absence ou contenu d'un fichier ; motif textuel interdit | règle Archgate |
| Dépendances entre modules JS/TS, Python… | l'outil déjà présent dans le projet (dependency-cruiser, import-linter…) ou une règle Archgate avec `ctx.ast` |
| Comportement à l'exécution (livraison de messages, reprises, sécurité) | tests d'intégration |
| Compromis métier, choix de fournisseur | revue humaine, critères écrits |

Pour Java : lire d'abord les tests ArchUnit existants, les compléter quand c'est pertinent, vérifier qu'ils importent les classes de **tous** les modules concernés (un test vert sur un sous-ensemble ne prouve rien pour le reste), les garder dans le build existant, ne pas dupliquer leur logique en TypeScript.

## Éprouver un nouveau contrôle

Tout nouveau contrôle est essayé sur **un cas conforme et une violation représentative**, dans des fixtures ou un environnement temporaire (dossier temporaire, arbre de travail Git détaché). Jamais de violation volontaire ni de faux ADR accepté dans l'application.

Un contrôle qui n'a jamais échoué vise peut-être le mauvais périmètre : vérifier les motifs de fichiers et la sélection par diff (voir `archgate.md`).

## Trois catégories de résultat, jamais mélangées

| Catégorie | Définition | Preuve |
|---|---|---|
| **Violation prouvée** | un contrôle exécuté a échoué, ou l'écart est démontré par `fichier:ligne` contre une contrainte écrite sans ambiguïté | sortie de commande, ou citation des deux textes |
| **Suspicion (revue IA)** | lecture du code qui suggère un écart, sans contrôle qui le démontre | indices, et ce qui manque pour conclure |
| **Absence de contrôle** | aucune règle ni test ne couvre la contrainte, ou le contrôle n'a pas tourné | ce qui manque : règle, test, outil, périmètre |

À côté, deux états de contrôle à ne pas confondre avec un succès :

- **Non exécuté** : outil absent, build impossible, contrôle sauté par la sélection par diff, ignoré volontairement. Toujours listé, avec la raison.
- **Exécuté sans règle pertinente** : la commande a rendu 0 mais aucune règle ne portait sur le changement. Ce n'est **pas** une conformité démontrée.

« Conforme » ne s'écrit que pour une contrainte donnée, couverte par un contrôle nommé qui a réellement tourné sur le périmètre nommé.

## Garde-fous

- Ne pas affaiblir un contrôle pour faire passer le code : pas de règle assouplie, de test désactivé, de suppression d'avertissement, de `continue-on-error`, de périmètre réduit.
- Ne pas modifier une décision pour qu'elle corresponde au code.
- Un contrôle de changement (diff) ne se présente jamais comme un audit complet.
- Un échec dû à l'environnement n'est pas un défaut de l'application.
