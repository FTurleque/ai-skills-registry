# Archgate CLI : ce qui a été vérifié

Observé avec **Archgate 0.59.0** sous Windows 10, par exécution. Pour toute autre version : `archgate <commande> --help` fait foi. Le CLI s'utilise sans compte ; le plugin Archgate est un produit distinct (bêta, connexion requise) dont ces skills ne dépendent pas.

## Commandes utiles

| Commande | Effet | Écrit sur le disque ? |
|---|---|---|
| `archgate --version` | version | non |
| `archgate doctor` | environnement, nombre d'ADR, nombre d'ADR avec règles, `logged_in` | non |
| `archgate adr list` | ADR reconnus : `id`, `title`, `domain`, `rules` (JSON hors terminal interactif) | non |
| `archgate adr show <id>` | un ADR | non |
| `archgate check [options] [fichiers…]` | exécute les règles des ADR `rules: true` | régénère `.archgate/rules.d.ts` |
| `archgate review-context` | ADR concernés par les fichiers modifiés | non |
| `archgate adr create`, `adr update`, `adr import`, `init` | écrivent | oui — sur demande seulement |

Options de `check` : `--staged`, `--base [ref]`, `--adr <id>`, `--verbose`, `--strict`, `--output console|json|github|sarif`. Il n'existe ni `--json` ni `--ci` sur `check`.

Codes de sortie de `check` : `0` aucune violation, `1` violation (ou avertissement avec `--strict`), `2` erreur d'exécution d'une règle.

## Le piège : un contrôle vert qui n'a rien exécuté

`check` ne lance un ADR que si **au moins un fichier modifié** correspond à son champ `files`. L'ensemble des fichiers modifiés = diff avec la branche de base **plus** l'arbre de travail (fichiers modifiés, indexés, non suivis).

| Situation | Résultat observé |
|---|---|
| Arbre propre, `HEAD` = branche de base | toutes les règles s'exécutent (`total` = nombre de règles) |
| Un seul fichier **sans rapport** modifié ou non suivi | ADR sauté : `pass: true`, `total: 0`, code `0` |
| Idem, avec une violation déjà présente dans la base | **toujours** `pass: true`, `total: 0`, code `0` |
| Idem avec `--adr <id>` ou un fichier du périmètre en argument | toujours `total: 0` : ces options restreignent, elles ne forcent pas |
| Fichier du périmètre modifié, violation | `pass: false`, code `1`, fichier et ligne |
| Arbre propre + `--base HEAD` (diff vide) | toutes les règles s'exécutent, violations héritées comprises |
| Arbre sale + `--base HEAD` | de nouveau filtré par les fichiers modifiés |

Conséquences pour tout contrôle :

1. Lire `total`, `passed`, `failed` et `results` avec `--verbose --output json`. **`total: 0` signifie « aucune règle exécutée », pas « conforme ».**
2. Comparer `total` au nombre de règles attendues : `adr_with_rules_count` de `archgate doctor` donne le nombre d'ADR porteurs de règles ; chaque fichier `.rules.ts` liste ses règles.
3. **Contrôle d'un changement** : `archgate check --verbose --output json` (ou `--staged`). Couvre uniquement les ADR dont le périmètre est touché. Le dire.
4. **Audit global** : il faut un diff vide. Dans un arbre propre : `archgate check --base HEAD --verbose --output json`. Si l'arbre est sale, ne pas le nettoyer : créer un arbre de travail temporaire détaché (`git worktree add --detach <dossier-temporaire> HEAD`), y lancer la même commande, puis le retirer (`git worktree remove`). Choisir un dossier temporaire au **chemin court** : sous Windows, Git a refusé un emplacement trop long. L'audit porte alors sur `HEAD` : le travail non commité **n'est pas** couvert, à signaler.
5. Un ADR sans champ `files` s'exécute toujours.
6. La trace `archgate --log-level debug check` montre `Skipping ADR <id>: scope untouched` : c'est la preuve qu'un ADR a été sauté.

## Format d'un ADR

Emplacement `.archgate/adrs/`, fichier `{ID}-{slug}.md`, règles facultatives dans `{ID}-{slug}.rules.ts`.

| Champ | Obligatoire | Note |
|---|---|---|
| `id` | oui | convention `PREFIXE-NNN` |
| `title` | oui | |
| `domain` | oui | `backend` (BE), `frontend` (FE), `data` (DATA), `architecture` (ARCH), `general` (GEN), ou domaine ajouté par `archgate adr domain add` |
| `rules` | oui | booléen ; `true` exige le fichier compagnon |
| `files` | non | globs du périmètre ; absent = tout le projet |
| `respectGitignore` | non | `true` par défaut |

Le schéma **n'a pas de champ de statut ni de date**. Des champs supplémentaires (`status`, `date`) ont été tolérés à l'analyse en 0.59.0 mais `archgate adr list` ne les restitue pas : écrire le statut dans le corps, et ne pas compter sur l'outil pour le suivre. Sections recommandées par l'outil, non imposées : `Context`, `Decision`, `Do's and Don'ts`, `Consequences`, `Compliance and Enforcement`, `References`. Garder ces intitulés quand le projet utilise Archgate ; le contenu peut être en français.

## Écrire une règle

```ts
/// <reference path="../rules.d.ts" />
export default {
  rules: {
    "identifiant-de-regle": {
      description: "Ce que la règle vérifie",
      async check(ctx) {
        for (const file of ctx.scopedFiles) {
          for (const m of await ctx.grep(file, /motif/)) {
            ctx.report.violation({ message: "…", file: m.file, line: m.line, fix: "…" });
          }
        }
      },
    },
  },
} satisfies RuleSet;
```

- Contexte : `scopedFiles`, `changedFiles`, `readFile`, `readJSON`, `grep`, `grepFiles`, `glob`, `ast` (TypeScript, JavaScript, Python, Ruby), `fileAtBase`, `projectRoot`. Rapports : `report.violation` (code 1), `report.warning`, `report.info`.
- Imports limités à `node:path`, `node:url`, `node:util`, `node:crypto`. 30 secondes par règle.
- Pas d'analyse syntaxique Java : une règle sur du Java est une recherche textuelle. Pour des dépendances entre couches ou des cycles, un test ArchUnit dans le build est l'outil adapté ; l'ADR y renvoie, on ne duplique pas sa logique en TypeScript.
- Ne jamais écrire `rules: true` sans fichier compagnon réel, ni déclarer une contrainte « automatisée » avant d'avoir vu la règle échouer sur une violation.

## Initialiser sans le plugin

Ces skills n'initialisent rien d'eux-mêmes. Si l'utilisateur demande une initialisation :

- `archgate init` crée `.archgate/adrs/GEN-001-example.md`, `.archgate/lint/README.md`, `.archgate/config.json` (branche de base), ajoute `.archgate/rules.d.ts` au `.gitignore`.
- Avec `--editor claude`, il écrit aussi `.claude/settings.local.json` avec `"agent": "archgate:developer"` et des permissions `Skill(archgate:…)` — **même quand le plugin n'est pas installé**. Relire ce fichier après coup et le faire corriger si le plugin n'est pas voulu. Aucun paramètre documenté ne désactive cette écriture : ne pas en inventer.
- Sans identifiants (`archgate doctor` → `logged_in: false`), l'installation du plugin est ignorée. Avec des identifiants valides, elle peut se déclencher **sans** `--install-plugin` : vérifier `doctor` avant.
- L'ADR d'exemple n'est pas une décision du projet : le retirer ou le remplacer, ne jamais le laisser comme décision acceptée.
- `archgate adr import` vise des packs et des dépôts Git ; ce n'est pas une conversion sans perte d'un dossier Markdown local.

## Autres constats

- La télémétrie anonyme est **activée par défaut** (`archgate telemetry status`, `archgate telemetry disable`, ou `ARCHGATE_TELEMETRY=0`). C'est un réglage de l'utilisateur : l'en informer, ne pas le changer.
- Sous Windows, le paquet npm télécharge le binaire au premier lancement et le décompresse avec `powershell` : si `powershell.exe` n'est pas dans le `PATH`, ce premier lancement échoue.
