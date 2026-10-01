# Guide de contribution

Merci de votre intérêt pour ce projet. Ce document décrit l'essentiel ; le processus détaillé est
dans [docs/contributing.md](docs/contributing.md).

---

## Prérequis

- Savoir quel **type** d'artefact vous ajoutez : la règle de rangement est dans
  [docs/architecture.md](docs/architecture.md), et c'est la décision la plus importante.
- Connaître les conventions du dépôt : [docs/conventions.md](docs/conventions.md).
- Python 3.8+ avec `pyyaml` et `jsonschema` pour lancer la validation.

---

## Processus rapide

1. Copier le gabarit du type depuis `templates/`
2. Renseigner les métadonnées et rédiger la documentation, limites comprises
3. Ajouter au moins un exemple réel
4. `python tools/validate.py && python tools/generate_index.py`
5. Mettre à jour `CHANGELOG.md` et la matrice de `docs/surfaces.md`
6. Ouvrir une pull request avec la checklist complétée

---

## Ce qui sera refusé

- Un artefact sans `README.md` utilisable, ou sans ses limites documentées.
- Un chemin absolu local, ou un secret, même de test.
- Un artefact jamais exercé déclaré `stable`.
- Un hook dont l'effet de bord n'est pas écrit : il s'exécute sans être appelé, donc son README est
  une condition d'entrée.
- Tout ce qui demande à Claude de valider sans réserve, de taire un désaccord ou de cesser de
  vérifier. Un artefact décrit comment travailler, jamais quoi conclure.

---

## Code de conduite

- Respecter les autres contributeurs
- Proposer des améliorations constructives
- Ne pas inclure de secrets, jetons ou informations personnelles

---

## Licence

En contribuant, vous acceptez que vos contributions soient distribuées sous la
[licence MIT](LICENSE) de ce dépôt.
