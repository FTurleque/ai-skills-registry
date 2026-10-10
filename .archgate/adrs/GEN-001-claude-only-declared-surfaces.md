---
id: GEN-001
title: Ne cibler que Claude, sur des surfaces déclarées et vérifiées
domain: general
rules: false
files: ["schemas/**", "docs/surfaces.md", "skills/**", "plugins/**", "agents/**", "commands/**", "hooks/**", "instructions/**", "mcp/**", "output-styles/**"]
---

# Ne cibler que Claude, sur des surfaces déclarées et vérifiées

## Context

Un artefact ne fonctionne pas partout : un hook n'existe que là où il y a des hooks, un script ne tourne pas sur claude.ai. Le lecteur du catalogue doit savoir où un artefact fonctionne réellement.

Faits établis, source [docs/surfaces.md](../../docs/surfaces.md) :

- « Le registre ne cible que Claude. Les autres assistants ne sont pas une dimension de ce dépôt : ce qui est portable au-delà de Claude le reste par nature, mais ce n'est ni déclaré, ni testé, ni documenté ici. »
- Quatre surfaces : `claude-code`, `claude-desktop`, `claude-ai`, `claude-api`. Toute autre valeur de `compatibility` est une erreur de validation.
- Une coche de la matrice signifie « déclaré compatible et vérifié sur au moins un cas d'usage réel ».

Ces règles sont entrées dans le dépôt avec le commit `3a04400` du 2026-10-02.

**Alternatives :** aucune étude n'est consignée (un registre multi-assistants, par exemple). Question ouverte : ce périmètre est-il définitif ou provisoire.

## Decision

**Statut : acceptée (2026-10-10).** Reprise de règles déjà en vigueur ; acceptée comme ADR par le mainteneur le 2026-10-10. Responsable : Fabrice Turleque.

- Le registre ne déclare, ne teste et ne documente que des surfaces Claude.
- `compatibility` MUST ne contenir que les quatre surfaces de l'énumération du schéma.
- Une surface MUST NOT être déclarée sans avoir été exercée sur un cas d'usage représentatif. Une surface plausible mais non essayée ne se déclare pas.
- Chaque artefact MUST figurer dans la matrice de `docs/surfaces.md`.

Périmètre : le champ `compatibility` de tous les artefacts, l'énumération du schéma, `docs/surfaces.md`.

## Do's and Don'ts

### Do
- Dire dans le `README.md` d'un artefact ce qui a été vérifié et ce qui ne l'a pas été.

### Don't
- Ne pas cocher une surface « par cohérence » avec un artefact voisin.

## Consequences

### Positive
- Le catalogue ne promet que ce qui a été essayé.

### Negative
- Des artefacts portables restent déclarés sur une seule surface tant que personne ne les a essayés ailleurs.

### Risks
- Ajouter une surface, ou un autre assistant, change l'énumération du schéma et toute la matrice.

## Compliance and Enforcement

### Automated Enforcement
- `python tools/validate.py` : valeurs de `compatibility` limitées aux surfaces connues ; avertissement si un artefact manque dans la matrice (`--strict` en fait une erreur). Exécuté par la CI.
- Aucune règle Archgate.

### Manual Enforcement
- **La véracité des coches** : aucun outil ne peut vérifier qu'une surface a réellement été essayée. C'est le cœur de la décision, et il relève de la relecture de PR.

## References

- [docs/surfaces.md](../../docs/surfaces.md)
- [docs/conventions.md](../../docs/conventions.md) — sens du statut d'un artefact
