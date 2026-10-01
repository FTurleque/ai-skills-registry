# Skills

Une **skill** est un fichier d'instructions que Claude charge quand la tâche s'y prête. Rien ne
s'exécute : c'est du texte qui change la façon dont Claude travaille, plus d'éventuelles ressources
qu'il peut lire ou lancer lui-même.

C'est le format d'Anthropic, et le plus portable du dépôt : la même skill fonctionne dans Claude
Code, dans l'application de bureau, sur claude.ai et via l'API, pour autant que son contenu ne
dépende pas de capacités propres à une surface.

## Forme attendue

```text
skills/<catégorie>/<nom-du-skill>/
├── SKILL.md        instructions, avec front matter YAML (obligatoire)
├── metadata.yaml   mêmes métadonnées, exploitables par l'outillage (obligatoire)
├── README.md       présentation lisible sans ouvrir SKILL.md (obligatoire)
├── examples/       au moins un cas d'usage réel
└── resources/      scripts, gabarits, références lues par Claude (facultatif)
```

Le dossier `<catégorie>` est la catégorie fonctionnelle, et elle doit être égale au champ
`category` des métadonnées. Les catégories existantes se lisent dans l'arborescence ; en créer une
nouvelle est permis, il suffit de la documenter dans `docs/architecture.md`.

## Ce qui déclenche une skill

Le champ `description` est ce qui décide du chargement. Il doit dire **quand** utiliser la skill,
pas seulement ce qu'elle fait : « Analyse du code Java pour identifier les défauts, risques et
améliorations » déclenche mieux que « Revue de code ».

## Installation et usage

| Surface | Comment |
|---------|---------|
| Claude Code | copier le dossier dans `~/.claude/skills/<nom>/`, ou le livrer dans un plugin |
| Application de bureau | ajouter la skill dans les réglages, ou la fournir via un plugin |
| claude.ai | téléverser le dossier dans les skills du compte ou du projet |
| API / Agent SDK | pointer le chemin du dossier dans la configuration de l'agent |

Voir [docs/install.md](../docs/install.md) pour les commandes exactes.

## Ajouter une skill

1. `cp -r templates/skill-template skills/<catégorie>/<nom>/`
2. Renseigner le front matter de `SKILL.md` **et** `metadata.yaml` — les deux doivent concorder, le
   validateur le vérifie.
3. Rédiger les instructions, ajouter un exemple réel.
4. `python tools/validate.py && python tools/generate_index.py`
5. Mettre à jour `CHANGELOG.md` et la matrice de [docs/surfaces.md](../docs/surfaces.md).
