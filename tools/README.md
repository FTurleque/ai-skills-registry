# Outils du dépôt

Deux scripts, sans dépendance lourde : `pyyaml` est requis, `jsonschema` est utilisé s'il est
présent et remplacé par une validation réduite sinon.

```bash
pip install pyyaml jsonschema
```

---

## `validate.py`

```bash
python tools/validate.py                # valide le dépôt
python tools/validate.py --strict       # les avertissements deviennent des erreurs
python tools/validate.py --json         # sortie machine, pour la CI
python tools/validate.py --self-test    # vérifie le validateur sur des cas construits
python tools/validate.py --root ../autre-depot
```

Code de sortie 0 si tout va bien, 1 sinon.

### Ce qu'il vérifie

**Par artefact**

- métadonnées conformes à `schemas/artifact.schema.json`, champs inconnus refusés ;
- `kind` cohérent avec le dossier de premier niveau ;
- `name` égal au nom du dossier, ou du fichier sans extension ;
- `category` égal au dossier parent, pour une skill ;
- présence des fichiers obligatoires du type ;
- front matter d'un `SKILL.md` identique à son `metadata.yaml` sur `kind`, `name`, `version`,
  `description`, `status` et `compatibility` ;
- identifiant unique dans tout le dépôt, tous types confondus.

**Par plugin**

- `plugin.json` lisible, `name` égal au nom du dossier ;
- `hooks.json` lisible, chaque handler porte un `command` ou un `args` ;
- avertissement si les chemins n'utilisent pas `${CLAUDE_PLUGIN_ROOT}`.

**Pour le dépôt**

- tout plugin de `plugins/` est déclaré dans la marketplace, et réciproquement ;
- chaque `source` de la marketplace existe et ne remonte pas hors du dépôt ;
- aucun chemin absolu local dans un fichier texte — **erreur**, pas avertissement ;
- aucun secret au format reconnaissable : clé AWS, jeton GitHub ou Slack, JWT, clé privée ;
- `INDEX.md` à jour ;
- avertissement si un artefact manque dans la matrice de `docs/surfaces.md` ;
- avertissement sur les fins de ligne CRLF.

### Ce qu'il ne vérifie pas

Il ne lit pas le contenu rédigé. Il ne sait pas si une `description` déclenche bien, si un exemple
est réel, si une coche de la matrice des surfaces est vraie, ni si un mot de passe quelconque se
cache dans une chaîne de connexion. Ces points restent à la relecture.

---

## `generate_index.py`

```bash
python tools/generate_index.py          # réécrit INDEX.md
python tools/generate_index.py --check  # échoue si INDEX.md n'est pas à jour
```

`INDEX.md` est entièrement regénéré : ne pas l'éditer à la main. Le script lit les métadonnées de
chaque artefact et produit un tableau par type, avec description, version, statut et surfaces.

---

## Ajouter un type d'artefact

Les deux scripts se pilotent par une table. La procédure complète est dans
[`docs/architecture.md`](../docs/architecture.md), section « Ajouter un type d'artefact au
registre » : énumération `kind` du schéma, dictionnaire `KINDS` du validateur, `KIND_LABEL` et
`KIND_ORDER` du générateur.

---

## Conventions des scripts

- Bibliothèque standard d'abord, dépendances justifiées.
- Un `--self-test` quand le script porte une logique de décision : un garde-fou qui ne s'auto-teste
  pas finit par passer à côté de ce qu'il devait attraper.
- Ces scripts ne sont pas des artefacts du registre : ils ne sont ni installables ni versionnés
  individuellement.
