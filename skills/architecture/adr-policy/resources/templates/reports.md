# Gabarits de restitution

Restitutions courtes, dans la conversation par défaut. Un fichier de rapport n'est écrit que si l'utilisateur le demande ou si le projet a un emplacement prévu.

## Contexte découvert (commun aux trois skills)

```markdown
**Contexte** — racine : `<chemin relatif ou nom>` · branche : `<…>` (arbre <propre|modifié>)
- Technologies et modules : <liste complète ; « non examiné : … » le cas échéant>
- Registre d'ADR : <emplacement(s) | aucun>
- arc42 : <emplacement, index §9 | absent>
- OpenSpec : <version, schéma, changements en cours | absent>
- Archgate : <version, n ADR dont m avec règles | CLI absent | non initialisé>
- Tests d'architecture : <…| aucun>
- Conventions locales appliquées : <…| aucune>
```

## Rapport d'audit (`adr-audit`)

```markdown
### Inventaire

| ID | Titre | Emplacement | Statut déclaré | Réalité observée | Périmètre | Contrôles | Recommandation |
|---|---|---|---|---|---|---|---|

### Constats

Pour chacun : ce qui est observé · preuve (`fichier:ligne`, commande) · étiquette (fait établi / hypothèse / question ouverte).

- Doublons et registres multiples
- Contradictions (entre ADR ; entre ADR et code, arc42, OpenSpec)
- Décisions obsolètes ou mal classées
- Références cassées (modules, vues arc42, changements, contrôles)

### Décisions structurantes non documentées — propositions à confirmer

| Observation dans le code | Pourquoi ce serait une décision | Ce qu'on ignore |
|---|---|---|

### Actions

- Applicables sans arbitrage (éditorial) : <liste>
- À faire valider : <liste, avec proposition concrète>

### Couverture de l'audit

Examiné : <…> · Partiel : <…> · Non examiné : <…>
```

Recommandation, une par document : **conserver**, **clarifier**, **regrouper** (brouillons seulement), **remplacer**, **reclasser**, **faire confirmer**.

## Verdict de pertinence (`adr-author`)

```markdown
**Demande** : <reformulation en une phrase>

1. Décision durable à mémoriser : <réponse | aucune>
2. Impact, compromis, coût de retour arrière : <réponse>
3. Couverture par l'existant : <ADR lus, et pourquoi ils couvrent ou non>

**Conclusion : <l'une des cinq, mot pour mot>**

<Selon le cas : lien vers l'ADR · modification proposée · brouillon · orientation vers un autre document.>
Validation humaine requise pour : <… | rien>
```

## Rapport de contrôle (`adr-check`)

```markdown
**Mode** : <changement (base `<ref>`, n fichiers) | audit global (état contrôlé : `<HEAD…>`)>

### ADR applicables

| ID | Pourquoi il s'applique | Contrôle prévu |
|---|---|---|

### Contrôles

| Contrôle | Commande | Résultat | Couverture réelle |
|---|---|---|---|
| Règles Archgate | `<…>` | <n exécutées / m attendues, k en échec> | <ADR et motifs de fichiers> |
| Tests du projet | `<…>` | <…> | <modules et classes> |
| Liens et index arc42 | `<…>` | <…> | <fichiers> |

### Résultats

- **Violations prouvées** : <ADR, règle ou test, fichier:ligne>
- **Suspicions (revue IA)** : <indices, ce qui manque>
- **Absences de contrôle** : <contrainte, ce qui manque>

### Non exécuté ou ignoré

<contrôle — raison>

### Vues arc42 et artefacts à mettre à jour

<sections, ou « aucune »>
```

Ne jamais écrire « conforme » en synthèse générale : seulement contrainte par contrainte, avec le contrôle qui le montre.
