# Processus de contribution

Comment créer et soumettre un artefact dans **AI Toolkit Registry**.

---

## 1. Choisir le type

C'est la seule décision difficile, et elle se prend avant d'écrire une ligne. La règle est dans
[architecture.md](architecture.md) : *le dossier dit le mécanisme, pas le sujet*.

| Ce que vous voulez | Type | Dossier |
|--------------------|------|---------|
| Que Claude sache faire quelque chose quand la tâche s'y prête | skill | `skills/<catégorie>/` |
| Que du code s'exécute automatiquement sur un événement | hook, ou plugin si c'est un ensemble | `hooks/` ou `plugins/` |
| Un assistant spécialisé avec ses propres outils | sous-agent | `agents/` |
| Un raccourci que vous tapez souvent | commande | `commands/` |
| Donner son contexte à un dépôt | instructions | `instructions/` |
| Brancher des outils externes | serveur MCP | `mcp/` |
| Changer la posture de réponse | style de sortie | `output-styles/` |
| Distribuer plusieurs de ces composants d'un bloc | plugin | `plugins/` |

En cas d'hésitation entre skill et sous-agent : si le travail doit se faire **à côté**, sans
encombrer la conversation, c'est un sous-agent. Si Claude doit simplement savoir comment s'y
prendre, c'est une skill.

---

## 2. Copier le gabarit

```bash
cp -r templates/skill-template skills/development/mon-skill
cp -r templates/plugin-template plugins/mon-plugin
cp templates/agent-template.md agents/mon-agent.md
cp templates/command-template.md commands/ma-commande.md
cp templates/output-style-template.md output-styles/mon-style.md
cp -r templates/hook-template hooks/mon-hook
cp -r templates/instructions-template instructions/mon-jeu
cp -r templates/mcp-template mcp/mon-serveur
```

Le nom est en kebab-case et décrit ce que l'artefact fait.

---

## 3. Renseigner les métadonnées

Le jeu complet est décrit dans le [README racine](../README.md#métadonnées--un-seul-schéma) et
validé par [`schemas/artifact.schema.json`](../schemas/artifact.schema.json).

Trois pièges fréquents :

- **`name` doit être égal au nom du dossier ou du fichier.** Le validateur refuse l'écart.
- **Pour une skill, `category` doit être égal au dossier parent.** Idem.
- **`description` décide du déclenchement** d'une skill, d'un sous-agent ou d'une commande. Écrire
  quand l'utiliser, pas seulement ce que ça fait.

Si l'artefact a un `SKILL.md` **et** un `metadata.yaml`, les deux doivent porter exactement les
mêmes valeurs. C'est redondant, c'est assumé — le `SKILL.md` sert à l'outil, le `metadata.yaml` à
l'outillage du dépôt — et le validateur refuse une divergence.

---

## 4. Rédiger

Le `README.md` répond à quatre questions, dans cet ordre : qu'est-ce que c'est, ce que ça change
concrètement, comment on l'installe, où sont les limites.

Les limites sont obligatoires. Un artefact dont les angles morts ne sont pas écrits est un piège
pour celui qui l'installera dans six mois — vous compris.

Ajouter au moins un exemple réel dans `examples/` : une entrée, le résultat, et pourquoi c'est le
bon résultat. Un exemple inventé ne vaut rien ; un exemple issu d'un vrai usage vaut la
documentation.

---

## 5. Valider

```bash
pip install pyyaml jsonschema
python tools/validate.py
python tools/generate_index.py
```

Pour un plugin, en plus :

```bash
claude plugin validate ./plugins/mon-plugin --strict
claude plugin validate .
```

Et l'essayer pour de vrai avant de le déclarer `stable`. Un artefact jamais exercé est un `draft`,
quelle que soit la qualité de sa documentation.

---

## 6. Mettre à jour le dépôt

- `CHANGELOG.md` : une entrée sous `[Non publié]`, section `Ajouté`, `Modifié` ou `Retiré`.
- `docs/surfaces.md` : une ligne dans la matrice, avec seulement les surfaces que vous avez
  essayées.
- `.claude-plugin/marketplace.json` : pour un plugin, l'entrée correspondante.
- `docs/architecture.md` : si vous créez une catégorie de skill.

---

## 7. Ouvrir la pull request

Remplir la checklist du gabarit de PR. La validation tourne automatiquement ; une PR rouge ne se
relit pas.

---

## Modifier un artefact existant

1. Incrémenter sa `version` selon SemVer : `PATCH` pour une correction sans changement de
   comportement, `MINOR` pour un ajout rétrocompatible, `MAJOR` pour un changement qui casse un
   usage existant.
2. Reporter la version dans `metadata.yaml` **et** dans le front matter du `SKILL.md`.
3. Documenter dans `CHANGELOG.md`.
4. Revalider et régénérer l'index.

## Retirer un artefact

Passer son `status` à `deprecated`, dire dans son `README.md` par quoi le remplacer et à partir de
quand, et attendre au moins une version du dépôt avant de supprimer les fichiers. Pour un plugin,
prévenir dans le `CHANGELOG.md` : une désinstallation est une action de l'utilisateur, pas la vôtre.
