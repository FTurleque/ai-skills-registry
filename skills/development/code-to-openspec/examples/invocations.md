# Exemples d'invocation

Le skill se déclenche à partir de la demande ; on peut aussi le nommer (`/code-to-openspec` dans Claude Code quand il est installé). Aucune question préalable n'est attendue sauf projet ambigu.

## Audit global

> Analyse cette application et prépare les corrections avec OpenSpec.

> Audite ce monorepo : cartographie, parcours critiques, problèmes prioritaires. Prépare les changements OpenSpec pour les défauts confirmés.

Attendu : cartographie, registre de couverture, constats par priorité, plan de correction, quelques changements pour les défauts confirmés, couverture honnête sur ce qui n'a pas été vu.

## Analyse ciblée

> Le total de la commande est faux avec une remise de 10 % sur 125 centimes. Analyse ce bug, ajoute un test de reproduction et prépare le changement OpenSpec.

> Retrouve les spécifications de la fonctionnalité d'export à partir du code.

> Audite le module `billing` avant que je le refactorise.

Attendu pour la dernière : une description de l'existant (non normative), les risques, les tests de caractérisation utiles, et seulement ensuite des propositions.

## Comparaison et contradictions

> Compare le code aux spécifications OpenSpec existantes de la capacité `order-total`.

> La documentation dit que le stock ne peut pas être négatif, le code l'autorise. Qu'en est-il ?

Attendu : contradiction affichée avec les deux sources ; *décision à clarifier* si rien ne permet de trancher ; pas de choix silencieux.

## Reprise

> Reprends l'audit de `docs/audit/orders/` : le code a changé depuis la dernière passe.

Attendu : lecture de `state.md`, dérive des preuves (`audit_tool.py drift`), constats revérifiés (résolu, inchangé, obsolète), pas de constat recréé, décisions de l'utilisateur intactes.

## Implémentation (demande explicite)

> Applique le changement `fix-discount-rounding`.

Attendu : le workflow d'application d'OpenSpec (ou `tasks.md` dans l'ordre), vérification par tâche, cases cochées, constat mis à jour. Pas de commit sans demande.

## Contrôle déterministe (facultatif, Python 3.8+)

```bash
python resources/audit_tool.py check    --audit-dir docs/audit/orders
python resources/audit_tool.py snapshot --audit-dir docs/audit/orders
python resources/audit_tool.py drift    --audit-dir docs/audit/orders
python resources/audit_tool.py next-id  --audit-dir docs/audit/orders
```
