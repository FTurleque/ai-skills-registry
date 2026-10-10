# Deux contrôles sur un projet de test

Sessions du 10 octobre 2026 : Claude Code 2.1.292 en mode non interactif, Archgate CLI 0.59.0, skill installé en portée utilisateur. Rapports abrégés.

## Contexte

Application Java à trois modules. `ARCH-001` (accepté) interdit au module `domain` d'importer `storage`, `web` ou `jakarta.persistence` ; une règle Archgate le vérifie sur `domain/**/*.java`. `DATA-001` (accepté) n'a aucun contrôle automatisé. Le `pom.xml` racine déclare trois modules qui n'ont pas de `pom.xml` : le build Maven ne peut pas tourner. Les violations ont été introduites dans des **copies temporaires** du projet, jamais dans une application.

## 1. Mode changement : une violation dans le diff

Branche `feat/order-notes`, deux fichiers ajoutés, dont `domain/…/OrderNotes.java` qui importe `jakarta.persistence.EntityManager`.

Entrée : `/adr-check`

Sortie :

```text
Contrôle terminé (aucun fichier modifié) : le changement viole ARCH-001, et le build Maven
documenté ne peut pas tourner.

Mode : changement (base `main`, 2 fichiers ajoutés). Ce n'est pas un audit complet du dépôt.

| Contrôle | Commande | Résultat | Couverture réelle |
| Règles Archgate | `archgate check --verbose --output json` | 1 exécutée / 1 attendue, 1 en échec (code 1) | ARCH-001 sur `domain/**/*.java` ; recherche textuelle des `import` seulement |
| Tests du projet | `mvn -q -o verify` | non exécuté : échec à la lecture des POM | aucune |
| Liens et index arc42 | `adr_tool.py check --root .` | 4 constats de forme, tous sur l'ancien registre | 4 ADR, §9 |

- Violation prouvée — ARCH-001, règle `domain-no-outward-imports` :
  `domain/src/main/java/com/acme/shop/domain/OrderNotes.java:3`, `import jakarta.persistence.EntityManager;`
- Suspicion (revue IA) — DATA-001 : un `EntityManager` dans `domain` suggère un accès à la
  persistance depuis le domaine, mais aucun appel n'existe encore et aucun contrôle ne le démontre.
- Absences de contrôle : dépendances Maven du module `domain` (pas de `domain/pom.xml`) ;
  DATA-001 : aucune règle ni test ; la règle ne voit pas un nom pleinement qualifié sans `import`.

Non exécuté ou ignoré : `mvn -q verify` — build impossible ; tests ArchUnit — il n'y en a pas.
```

## 2. Mode global : une violation héritée que le contrôle de changement ne voit pas

Branche `feat/readme` : le diff avec `main` ne contient que `NOTES.txt`, l'arbre porte un `TODO.txt` non suivi, et `main` contient déjà `domain/…/LegacyLookup.java` qui importe une classe de `storage`.

Entrée : `/adr-check global`

Sortie :

```text
Mode : audit global (état contrôlé : `HEAD` = `9cf7676`, dans un arbre de travail temporaire
détaché, retiré ensuite). `TODO.txt` n'est pas couvert.

| Règles Archgate | `archgate check --base HEAD --verbose --output json` (arbre propre sur `HEAD`) | 1 exécutée / 1 attendue, 1 en échec, code 1 | ARCH-001, les 3 fichiers de `domain/**/*.java` |

Violations prouvées
- ARCH-001 : `domain/src/main/java/com/acme/shop/domain/LegacyLookup.java:3` contient
  `import com.acme.shop.storage.OrderJpaRepository;`. L'écart date du commit `51336f8 legacy`.

Non exécuté ou ignoré
- `archgate check` tel que documenté, sur l'arbre courant : exécuté, mais `total: 0`, code 0. Sur
  cette branche, `NOTES.txt` et `TODO.txt` sont hors du périmètre d'ARCH-001, donc la règle est
  sautée. La commande du `CLAUDE.md` rend donc un résultat vert ici alors que la violation est
  dans `HEAD`.
- Travail non commité (`TODO.txt`) : hors audit.
```

Après la session : `git status` montre toujours `TODO.txt` non suivi et rien d'autre ; `git worktree list` ne liste plus que le dépôt.

## Notes

- Le second cas est la raison d'être du mode `global` : la commande que le projet documentait rendait vert.
- ArchUnit n'a pas pu être exercé (pas de build exécutable, aucun test) : le skill l'a écrit en « non exécuté » plutôt qu'en succès.
- Ces deux sessions avaient l'autorisation de lancer `archgate`, `git` et `mvn`. Dans une session précédente sans ces autorisations, les commandes ont été refusées et le rapport les a listées comme non exécutées.
- L'arbre de travail temporaire a dû être créé dans un dossier au chemin court : sous Windows, Git a refusé le premier emplacement, trop long.
