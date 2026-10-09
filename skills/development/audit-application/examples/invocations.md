# Exemples d'invocation

Les demandes suivantes déclenchent le skill `audit-application`.

## Audit complet

> Audite cette application.

Attendu : phase 0 (stack, carte du dépôt, 10 à 20 modules critiques), annonce du périmètre, six axes en parallèle, consolidation relue par un agent indépendant, puis livrables dans `docs/audit/<AAAA-MM-JJ>/` et artefact de synthèse.

## Audit ciblé sécurité

> Fais un audit de sécurité du dépôt, en profondeur.

Attendu : profil *sécurité* (axes 3 et 6 uniquement) ; inventaire des points d'entrée, puis suivi manuel des flux jusqu'aux sorties sensibles. Les secrets sont signalés par `fichier:ligne` et nature, jamais par valeur.

## Passe rapide

> Donne-moi l'état de santé du code, sans lecture exhaustive.

Attendu : profil *rapide* (architecture, qualité, sécurité sur le cœur du dépôt).

## Ce qui doit être produit

| Fichier | Contenu |
|---------|---------|
| `README.md` | synthèse exécutive de 2 à 3 pages |
| `findings.md` / `findings.json` | constats triés, avec sprint et dépendances |
| `sprints.md` / `sprints-meta.json` | ordre de correction, chemin critique, critères de sortie |
| `architecture.md` | découpage réel observé et diagramme Mermaid |
| `plan-action.md` | plan en trois temps, renvoi vers `sprints.md` pour l'ordre |
