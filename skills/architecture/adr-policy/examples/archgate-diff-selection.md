# Archgate : un contrôle vert peut n'avoir rien exécuté

Relevé du 10 octobre 2026, Archgate CLI 0.59.0, Windows 10. C'est la série d'essais dont `resources/archgate.md` tire ses règles.

## Contexte

Projet de test jetable : trois modules Java (`domain`, `storage`, `web`), un ADR `ARCH-001` avec `rules: true` et `files: ["domain/**/*.java"]`, une règle qui interdit dans `domain` les imports de `storage`, `web` et `jakarta.persistence`. Branche de base : `main`.

La « violation » est un fichier `domain/…/BadOrderStore.java` contenant `import jakarta.persistence.EntityManager;`.

## Entrée et sortie

Commande : `archgate check --verbose --output json`, avec les options indiquées.

| # | État du dépôt | Options | `pass` | `total` | Code |
|---|---|---|---|---|---|
| A | arbre propre, `HEAD` = `main`, code conforme | — | true | 1 | 0 |
| B | idem + un fichier `NOTES.txt` non suivi | — | true | **0** | 0 |
| B | idem | `--adr ARCH-001` | true | **0** | 0 |
| B | idem | un fichier de `domain/` en argument | true | **0** | 0 |
| C | violation commitée sur une branche de travail | — | false | 1 | 1 |
| C | idem | `--staged` (rien d'indexé) | false | 1 | 1 |
| D | violation fusionnée dans `main`, arbre propre | — | false | 1 | 1 |
| E | violation dans `main` + `NOTES.txt` non suivi | — | **true** | **0** | **0** |
| E | idem | `--adr ARCH-001` | **true** | **0** | **0** |
| G | violation dans `main`, branche qui ne modifie que `NOTES.txt` | — | **true** | **0** | **0** |
| G | idem | `--base HEAD` | false | 1 | 1 |
| H | idem + arbre sale | `--base HEAD` | **true** | **0** | **0** |
| I | arbre de travail détaché et propre sur le même commit | `--base HEAD` | false | 1 | 1 |

Trace de débogage du cas B (`archgate --log-level debug check`) :

```text
DEBUG: Loaded 1 rules from ARCH-001
DEBUG: Files changed since 1f958e4… (incl. working tree): 1
DEBUG: Skipping ADR ARCH-001: scope untouched
{"pass":true,"total":0,"passed":0,"failed":0, …}
```

## Notes

- Les cas E, G et H sont les dangereux : une violation existe dans le dépôt, la commande rend `pass: true` et le code 0, parce que les fichiers modifiés ne touchent pas le périmètre de l'ADR.
- `--adr` et les fichiers en argument **restreignent** la sélection ; ils ne forcent pas l'exécution.
- La documentation en ligne dit qu'un ensemble de fichiers modifiés vide déclenche une analyse complète : c'est exact (cas A, D, I). Ce qu'elle ne met pas en avant, c'est qu'un seul fichier sans rapport suffit à ne plus être dans ce cas.
- D'où les deux règles du skill `adr-check` : compter les règles exécutées (`total`) contre le nombre attendu, et faire l'audit global avec un diff vide (cas I), jamais avec la commande du contrôle de changement.
- Sous Windows, `git worktree add` a échoué dans un dossier temporaire au chemin très long ; un chemin court a fonctionné.
