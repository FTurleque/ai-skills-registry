# Gabarit d'ADR

Repli quand le projet n'impose pas son propre format. S'il en a un (gabarit, ADR existants, schéma d'outil), c'est lui qu'on suit, en y faisant entrer les rubriques ci-dessous.

Viser une page. Les études longues se lient, elles ne se recopient pas.

## Rubriques attendues, quel que soit le format

| Rubrique | Contenu |
|---|---|
| Identité | identifiant stable, titre, statut, date, responsables |
| Contexte | problème concret, contraintes déterminantes |
| Décision | choix, périmètre (tous les modules concernés), limites |
| Alternatives | options réellement envisagées, ou analyse datée d'aujourd'hui et présentée comme telle |
| Conséquences | bénéfices, coûts, compromis acceptés |
| Vérification | contrôles automatisés existants, commande, part laissée à la revue humaine |
| Traçabilité | changement OpenSpec, PR, vues arc42, ADR remplacé ou remplaçant |

## Variante Archgate

Fichier `.archgate/adrs/<ID>-<slug>.md`. Les intitulés de section restent ceux de l'outil ; le contenu est rédigé dans la langue du projet. Le schéma n'a pas de champ de statut : il s'écrit en tête de la décision.

```markdown
---
id: <PREFIXE-NNN>
title: <titre>
domain: <domaine enregistré>
rules: false
files: ["<motif>", "<motif>"]
---

# <titre>

## Context

<Problème et contraintes. Faits établis avec leur source ; hypothèses étiquetées comme telles.>

**Alternatives :**
- **<option>** — <pourquoi écartée>. <Étudiée à l'époque (source) | Analyse du <date>.>

## Decision

**Statut : proposée (<date>).** <Responsables.>

<Le choix, en termes observables : MUST / MUST NOT.>

Périmètre : <modules et dossiers concernés>. Hors périmètre : <…>.

## Do's and Don'ts

### Do
- <…>

### Don't
- <…>

## Consequences

### Positive
- <…>

### Negative
- <…>

### Risks
- <…>

## Compliance and Enforcement

### Automated Enforcement
- <Règle ou test existant, chemin, commande. « Aucun » si rien n'existe.>

### Manual Enforcement
- <Ce que la revue humaine vérifie.>

## References

- Changement OpenSpec : <lien>
- Vues arc42 : <sections>
- Remplace : <ID et lien> · Remplacé par : <ID et lien>
```

`rules: true` seulement quand le fichier `<ID>-<slug>.rules.ts` existe et a été éprouvé.

## Variante Markdown simple

Pour un registre de type `docs/adr/NNNN-titre.md`.

```markdown
# <NNNN>. <titre>

- Statut : proposé
- Date : <date>
- Responsables : <…>
- Remplace : <lien> · Remplacé par : <lien>

## Contexte

## Décision

Périmètre : <modules>.

## Alternatives

## Conséquences

## Vérification

| Contrainte | Contrôle | Commande | Couverture |
|---|---|---|---|
| <…> | <test, règle ou « revue humaine »> | `<commande>` | <modules couverts / non couverts> |

## Traçabilité
```

## Remplacer une décision acceptée

1. Nouvel ADR au statut *proposé*, avec « Remplace : <ancien> ».
2. L'ancien ADR **reste**. Une fois le remplacement accepté par une personne, son statut devient *remplacé* et il reçoit « Remplacé par : <nouveau> ». Son texte n'est pas réécrit.
3. L'index (arc42 §9) reflète les deux statuts.
