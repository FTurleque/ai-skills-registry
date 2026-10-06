# Changelog

Toutes les modifications notables de ce dépôt sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet respecte le [Versionnement Sémantique](https://semver.org/lang/fr/).

---

## [Non publié]

### Modifié — `source._extract_c` découpée (ticket #11)

Complexité 23 → quatre fonctions courtes : `_extract_c` (parcours des lignes et pile des classes
englobantes), `_function_on_line` (signature reconnue sur une ligne), `_function_from_signature` (corps entre
accolades, ou expression après `=>`, ou déclaration sans corps) et `_line_offsets`. La fenêtre de recherche du
corps devient une constante (`_BODY_SEARCH_WINDOW`). **Aucun changement de comportement** : référence produite
par l'ancien moteur (324 entrées), 24 scénarios du hook, et analyse complète du corpus et des fixtures (380 et
38 constats) identiques.

Même méthode que pour `check_identifiers` et `rules_security.check`, avec le même constat : sur le corpus
précédent, **7 mutations de l'ancien code sur 16 seulement étaient détectées** (classe jamais dépilée,
fonction fléchée, repli quand l'accolade fermante manque, corps décalé, modificateurs perdus, profondeur
d'accolade…). Le corpus a reçu des fichiers Java (classes imbriquées, interfaces, record, `throws` long,
accolades ou parenthèses non refermées), C#, Kotlin, Go, Rust et JavaScript, et le résumé des fonctions
conserve maintenant aussi les modificateurs et l'empreinte du corps : 16 sur 16 sur l'ancien code, 18 sur 18
sur le code découpé.

Deux comportements douteux de l'extracteur sont figés par la référence, non corrigés ici : une fonction à
corps d'expression sans accolades adopte l'accolade de la fonction suivante, et le receveur d'une méthode Go
est lu comme une fonction nommée `func`. Un moteur déjà installé doit être réinstallé.

### Modifié — `rules_security.check` découpée (ticket #11)

Complexité 23 → quatre fonctions courtes : `check` (parcours des lignes), `_line_findings` (les motifs d'une
ligne), `_is_false_match` (exceptions propres à certaines règles : valeur factice, alea sans mot-clé,
`literal_eval`, URL en test) et `_severity` (abaissement en code de test). Les seuils en dur deviennent des
constantes nommées (`_MAX_LINE_CHARS`, `_EVIDENCE_WIDTH`, `_COMMENT_PREFIXES`, `_KEEP_SEVERITY_IN_TESTS`).
**Aucun changement de comportement** : référence produite par l'ancien moteur (261 entrées), analyse complète
du corpus et des fixtures (378 et 38 constats) et 24 scénarios du hook identiques.

Le filet a dû être renforcé d'abord : 17 mutations de l'ancien code, **4 seulement détectées**. Corpus
complété (troncature des lignes de plus de 2000 caractères, secrets cités dans des commentaires de chaque
style, filtres de langue, valeurs factices, `exec` passant par `literal_eval`, exemptions de sévérité en
test) : 17 sur 17 sur l'ancien code, 19 sur 19 sur le code découpé.

### Corrigé — la sélection « une ligne sur trois » des tests ne filtrait rien

`SourceFile.is_changed` accepte une marge de 2 lignes : avec une ligne modifiée sur trois, chaque ligne est à
moins de 2 lignes d'une ligne modifiée, donc toutes passaient et les entrées `un_tiers` étaient identiques aux
entrées `tout`. Depuis la suite introduite plus haut, le filtre « ligne modifiée » n'était donc jamais exercé.
La sélection devient « une ligne sur sept » (`un_sur_sept`) ; la référence a été régénérée avec l'ancien moteur.

### Modifié — `rules_naming.check_identifiers` découpée (ticket #11)

La fonction faisait 105 lignes pour une complexité de 49. Elle devient une dizaine de fonctions courtes :
`_check_variables` (une ligne, ses noms déclarés, `_check_variable`), `_check_function_name`,
`_check_function_contract` (booléen, getter), `_check_function_case` et `_check_parameters`, autour d'un
`_Collector` qui garde la déduplication par (règle, nom, symbole). **Aucun changement de comportement** :
l'ordre des constats est conservé, et un bloc conditionnel sans effet (le « setter fluide », qui se terminait
par `pass`) est supprimé.

Vérifié avec la référence des tests **produite par l'ancien moteur** : 226 entrées identiques, plus l'analyse
complète du corpus et des fixtures (371 et 38 constats) champ par champ. Huit mutations ciblant la découpe sur
dix sont détectées ; les deux autres sont équivalentes (l'arrêt après la première abréviation est masqué par
la déduplication ; la validité d'identifiant d'un paramètre ne change rien sauf pour un nom avec tiret).

Pour y arriver, la première série de mutations n'en détectait que deux sur dix : le corpus a été renforcé
(abréviation et nom numéroté sur une même variable, noms de fonction composés, getters de longueur 4, 5 et
6, compteur de boucle jamais vu ailleurs, noms de paquet `util` et `data`) et un groupe `partial` ajouté à
la suite des règles (sélection d'une ligne sur trois). Un moteur déjà installé doit être réinstallé.

### Corrigé — `BUG.DIV_ZERO` ne signalait jamais `/ size()`

La règle cherchait `size\(\)\b` : or une borne de mot ne peut pas suivre une parenthèse fermante, donc
l'alternative `size()` ne correspondait jamais. Le motif devient `size\(\)|(?:length|count|total|n)\b` :
`return 100 / size();` est maintenant signalé, comme `/ count` et `/ total` l'étaient déjà.

Seules les écritures `/ size()` changent. `/ liste.size()` n'a jamais été signalé et ne l'est toujours pas :
élargir la règle aux appels sur un objet changerait sa portée et ferait l'objet d'une décision à part.
Sur le corpus de tests et les fixtures, l'analyse complète gagne un seul constat (`Complex.divisionBySize`).
Un moteur déjà installé doit être réinstallé.

### Modifié — tests de caractérisation étendus à toutes les règles

La suite `rules` ne couvrait que `check_lines`, `check_blocks` et `check_file` (33 des 71 règles du
moteur). Elle couvre maintenant **toutes** les règles : sécurité, nommage, imports inutilisés, complexité et
bugs par fonction, extraction des fonctions, duplication. 182 entrées au lieu de 80 ; les 80 d'origine ne
changent pas.

- Corpus complété : `Security`, `Naming`, `Complex`, `DuplicateA` et `DuplicateB` (Java), `security.py`,
  `naming.py` et `tests/test_security.py` (Python), `security.js`.
- Les valeurs ressemblant à des secrets (clé AWS, clé privée, JWT, jeton Slack et GitHub) sont assemblées à
  l'exécution : le validateur du dépôt et la protection des secrets de GitHub les refusent en clair.
- La couverture est calculée à partir des règles que le moteur déclare : ajouter une règle sans cas de
  corpus fait échouer le test.
- Validé par dix mutations (au moins une par famille de règles) : toutes détectées. La mutation d'une garde
  de division a d'abord échappé au test : le corpus ne contenait aucune division protégée. Il en contient
  maintenant trois, plus une non protégée.
- Défaut de règle relevé à cette occasion, corrigé dans l'entrée ci-dessus : `BUG.DIV_ZERO` ne signalait
  jamais `/ size()`.

### Modifié — petits points du superviseur de code (suite du ticket #11)

Aucun changement de comportement : l'analyse complète (règles de sécurité, de nommage, de duplication, de
complexité) du corpus de tests et des fixtures donne exactement les mêmes 300 constats qu'avant, et les deux
suites de caractérisation passent.

- `source.load` : un fichier illisible n'est plus ignoré par un `except Exception: continue` muet ;
  `_read_text` ne capture que `OSError` et le signale sur la sortie d'erreur.
- Les empreintes de `Finding.key()` (déduplication et anti-boucle) et de la détection de duplication passent
  de SHA-1 à SHA-256 ; elles ne servent qu'à comparer. Les états de session existants sont ignorés une fois.
- Variables `ret` renommées `return_type` (`source.py`, `rules_naming.py`).
- Le constat « commande construite à partir de valeurs dynamiques » sur `run_git` est documenté comme faux
  positif : liste d'arguments, sans shell, chemins toujours placés après `--`.

### Corrigé — faux positif de `BUG.DISABLED_TEST` sur `exit(`

Dans un fichier de test, la règle « test désactivé » cherchait `xit(` sans borne de mot, en insensible à la
casse : elle reconnaissait donc le `xit(` de `sys.exit(`, de `SystemExit(`, de `exit(` et de `process.exit(`.
Un `sys.exit(main())` en fin de script de test valait un MAJOR « test désactivé ». Le motif porte maintenant
une borne de mot (`\bxit`, `\bxdescribe`) : les vrais `xit(` et `xdescribe(` restent signalés.

Deux fichiers du corpus de tests le couvrent (`py/tests/test_exit.py`, `js/exit.test.js`) ; aucune entrée
existante de la référence ne change. Un moteur déjà installé doit être réinstallé.

### Ajouté — tests de caractérisation du superviseur de code

`plugins/code-supervisor/tests/` : un filet de sécurité pour les refactorisations du moteur, rejoué par la
CI (`python plugins/code-supervisor/tests/run_tests.py`). Il compare la sortie du moteur à des références
versionnées (`golden/`), sans dépendance au-delà de Python et de `git`.

- **`hook`** : 24 scénarios de bout en bout du hook (tours de blocage et libération anti-boucle, sessions,
  entrées invalides, transcript, état corrompu, chemin accentué, `--check`, `--self-test`).
- **`rules`** : `check_lines`, `check_blocks` et `check_file` sur un corpus statique écrit à la main, avec
  deux jeux de seuils et deux sélections de lignes ; échoue aussi si le corpus ne déclenche plus l'une des
  25 règles attendues.
- Validé par mutation : quatre régressions volontaires (seuils, filtre inversé, drapeau ignoré) sont toutes
  détectées. Les références sont indépendantes de la machine (dossier de travail normalisé, aucun chemin
  local).
- `.claude/supervisor.config.json` rend le superviseur silencieux sur le corpus et les fixtures, qui
  contiennent du code volontairement fautif.

### Corrigé — encodage du superviseur de code sous Windows

Quand Claude Code lance le hook, `stdin` et `stdout` sont des tubes : Python y utilise la page de codes
de Windows (cp1252) au lieu de l'UTF-8 que Claude Code envoie et lit. Trois effets :

- les accents des messages du superviseur arrivaient déformés (`�`) : octets cp1252 lus comme de l'UTF-8 ;
- la sortie du hook plantait (`UnicodeEncodeError`, code 1) dès qu'elle contenait un caractère absent de
  cp1252, par exemple une flèche dans la sortie d'un outil externe ; le verdict était alors perdu ;
- un dépôt dont le chemin contient un accent n'était pas trouvé : le chemin de la charge utile était mal
  décodé, et le superviseur ne relisait rien, sans le signaler.

Correctif : la charge utile est lue en UTF-8, la sortie du hook est du JSON en ASCII pur (accents
échappés), et les sorties redirigées du mode manuel (`--check`, `--self-test`) passent en UTF-8. L'auto-test
échoue si la lecture ou l'encodage régresse. Un moteur déjà installé doit être réinstallé.

### Sécurité — noms de fichiers dans les commandes `external_tools`

`{files}` était remplacé par les noms des fichiers modifiés, protégés par `shlex.quote`, puis la ligne
partait à `shell=True`. Or ces noms viennent du dépôt supervisé, et le quoting POSIX ne protège pas
`cmd.exe` : sous Windows, un fichier nommé `a&commande b.py` (nom valide) séparait la ligne de commande et
exécutait `commande`, même avec un outil déclaré par l'utilisateur. Un nom avec espace était aussi coupé en
deux arguments.

- Sous Windows, les noms passent entre guillemets doubles, et un nom qui contient un caractère que
  `cmd.exe` interprète même entre guillemets (`& | ^ < > % ! "` ou un caractère de contrôle) est écarté,
  avec un avertissement sur la sortie d'erreur. Ailleurs, `shlex.quote` reste le bon quoting.
- L'auto-test échoue si l'un de ces noms est de nouveau accepté.
- La passe d'analyse de duplication, optionnelle, signale sa panne sur la sortie d'erreur au lieu de
  l'avaler (`except Exception: pass`, relevé CRITICAL par le superviseur).
- Un moteur déjà installé doit être réinstallé pour en profiter. Suite : #11.

### Sécurité — le superviseur de code n'exécute plus rien venu de la configuration du projet

Le hook est installé globalement et lisait `<projet>/.claude/supervisor.config.json` et
`<projet>/.supervisor.json`, c'est-à-dire des fichiers du dépôt supervisé, qui peut être un dépôt tiers.
Trois clés de cette configuration désignaient un programme à lancer ou un emplacement d'écriture :

- `external_tools` : commandes lancées avec `shell=True` à la fin de chaque réponse d'agent ;
- `llm.cli` : programme lancé pour la relecture par modèle ;
- `log_dir` : dossier où le superviseur écrit ses rapports et son état.

Ces trois clés sont désormais ignorées dans une configuration de projet, avec un avertissement sur la
sortie d'erreur. Elles restent honorées dans `~/.claude/supervisor.config.json` et dans le fichier livré
avec le moteur. Tous les autres réglages restent surchargeables par projet. Effet de bord corrigé : une
liste `external_tools` déclarée par l'utilisateur n'est plus écrasée par celle d'un projet.

- **À faire si vous utilisiez `external_tools` dans un projet** : déplacer la déclaration dans
  `~/.claude/supervisor.config.json`.
- Un fichier de configuration qui n'est pas un objet JSON est ignoré au lieu de faire échouer le hook.
- L'auto-test échoue si une configuration de projet hostile parvient à fixer l'une de ces clés.
- Un moteur déjà installé doit être réinstallé pour en profiter. Suite : #11.

### Modifié — nettoyage des règles du superviseur de code

Aucun changement de comportement : sur un corpus de 129 fichiers (stdlib Python, JavaScript et
TypeScript réels, Java et Python synthétiques, fixtures) analysés avec deux jeux de seuils et deux
sélections de lignes modifiées, `check_lines`, `check_blocks` et `check_file` produisent exactement les
mêmes 32 848 constats qu'avant.

- `rules_bugs.check_lines` : les exceptions propres à chaque règle passent dans une table
  (`_SKIP_WHEN`) au lieu d'une cascade de `if`.
- `rules_bugs.check_blocks` : découpée en `_c_family_blocks`, `_catch_findings`,
  `_resource_leak_finding` et `_python_except_blocks`.
- `rules_quality.check_file` : découpée en `_file_findings`, `_form_findings` et
  `_magic_number_finding` ; les seuils en dur deviennent des constantes nommées.

### Modifié — nettoyage interne du superviseur de code

Aucun changement de comportement : 23 scénarios de bout en bout (payloads du hook, rounds anti-boucle,
transcript, état corrompu, `--check`, `--self-test`) donnent la même sortie qu'avant.

- La logique de `resources/supervisor.py` passe dans `resources/supervisor/runner.py`, découpée en
  petites fonctions (`hook_main`, `touched_files`, `log_dir_for`, `cli_main`, `self_test`).
  `supervisor.py` ne garde que le point d'entrée, qui place le moteur sur le chemin d'import : les six
  `# noqa: E402` disparaissent. Un moteur déjà installé doit être réinstallé (le nouveau module
  `runner.py` est copié par l'installateur).
- `llm.review` est découpée (`_build_prompt`, `_run_reviewer`, `_to_finding`).
- Les `except Exception` de `supervisor.py` et de `llm.py` sont restreints aux erreurs attendues ou
  journalisent sur stderr.
- L'empreinte anti-boucle passe de SHA-1 à SHA-256 : les états de session existants sont ignorés une
  fois, sans conséquence.
- `engine.counts` : la variable `res` devient `per_severity` (sans changement de comportement).

### Corrigé — faux positifs du superviseur de code

- `BUG.SUPPRESS` ne se déclenche plus sur un marqueur cité dans une chaîne ou dans un fichier de
  configuration (`# noqa` mentionné par une règle de documentation, par exemple) : il ne vise que les
  vraies suppressions, dans le code ou ses commentaires.
- `CNV.MAGIC_NUMBER` ne s'applique plus aux fichiers de configuration (`yaml`, `json`, `xml`) : leurs
  valeurs sont des données.
- L'auto-test échoue désormais si ces règles se déclenchent sur les fixtures `clean_*`. Un moteur déjà
  installé doit être réinstallé pour en profiter.

### Modifié — rapports du superviseur de code

- Les rapports et l'état anti-boucle s'écrivent désormais dans `<projet>/docs/rapport-supervisor/`
  et non plus dans `<projet>/.claude/supervisor/`. Le dossier porte son propre `.gitignore` (`*`) :
  les rapports ne sont jamais commités. Un moteur déjà installé doit être réinstallé pour en profiter.
- Ajout de `.claude/CLAUDE.md` et `.claude/settings.json` : configuration Claude partagée du dépôt.

### Modifié — restructuration du dépôt

Le dépôt s'appelait `ai-skills-registry` et rangeait tout sous `skills/`, y compris ce qui n'est pas
une skill. Chaque dossier de premier niveau porte désormais **un type d'artefact**, et son nom dit ce
que l'artefact est.

- Dépôt et marketplace renommés `ai-toolkit-registry`. Le nom de la marketplace est le suffixe
  d'installation des plugins : il passe de `@ai-skills-registry` à `@ai-toolkit-registry`, et une
  marketplace déjà ajoutée doit être retirée puis rajoutée.
- Nouvelle arborescence par type : `skills/`, `plugins/`, `agents/`, `commands/`, `hooks/`,
  `instructions/`, `mcp/`, `output-styles/`. Chacun porte un `README.md` qui documente le type, sa
  forme attendue et son installation.
- Le niveau `skills/shared/` est supprimé : la portabilité est déclarée par le champ `compatibility`,
  l'encoder aussi dans le chemin faisait la même information à deux endroits. Les skills vivent
  maintenant sous `skills/<catégorie>/<nom>/`.
- Les dossiers `skills/copilot/`, `skills/chatgpt/` et `skills/opencode/` sont supprimés. Le registre
  cible Claude et ses surfaces ; les autres assistants ne sont plus une dimension du dépôt.
- `schemas/skill.schema.json` devient `schemas/artifact.schema.json` et valide **tous** les types. Le
  champ `kind` devient obligatoire, le champ `compatibility` prend pour valeurs les surfaces Claude
  (`claude-code`, `claude-desktop`, `claude-ai`, `claude-api`), et les champs facultatifs `requires`,
  `homepage` et `replaces` apparaissent.
- `docs/compatibility.md` devient `docs/surfaces.md` : surfaces Claude au lieu d'outils IA.
- Nouveau `docs/install.md` : comment consommer chaque type d'artefact, par surface et par portée.
- Un gabarit par type dans `templates/`.

### Ajouté

- Plugin `code-supervisor` (`plugins/code-supervisor/`) : supervision automatique du code produit par
  un agent Claude Code. Hooks `Stop` et `SubagentStop`, moteur d'analyse statique portable sans
  dépendance (sécurité, bugs introduits, duplication, complexité, nommage, conventions), relecture
  par modèle via `claude -p`, et renvoi de l'agent en correction sur un constat bloquant. Installable
  comme plugin, et installable à la main.
- Le dépôt est une marketplace de plugins Claude Code : `.claude-plugin/marketplace.json` à la
  racine.
- Outillage du dépôt : `tools/validate.py` (métadonnées contre schéma, cohérence `kind` / chemin /
  `name` / `category`, fichiers obligatoires, front matter synchronisé avec `metadata.yaml`,
  manifestes de plugin et marketplace, absence de chemin absolu et de secret, index à jour) avec son
  `--self-test`, et `tools/generate_index.py` qui produit `INDEX.md`.
- `INDEX.md` : catalogue généré de tous les artefacts, par type.
- Workflow GitHub `validate` : auto-test du validateur, validation du registre, vérification de
  l'index et auto-tests des moteurs livrés, sur chaque pull request.
- Skill `generate-windows-exe` (`skills/development/generate-windows-exe/`) : génération d'un
  exécutable Windows via Inno Setup ou jpackage, avec un driver PowerShell reproductible.

### Déplacé

- `skills/shared/development/java-code-review/` → `skills/development/java-code-review/` (version
  1.1.0 : métadonnées au nouveau schéma)
- `skills/shared/development/generate-windows-exe/` → `skills/development/generate-windows-exe/`
  (version 1.1.0 : métadonnées au nouveau schéma)
- `skills/claude/code-supervisor/` → `plugins/code-supervisor/`

### Corrigé — revue par modèle du superviseur de code sous Windows

- Le prompt de la revue passe par l'entrée standard de `claude -p` et non plus en argument : un diff
  de plus de 30 000 caractères dépassait la limite de ligne de commande de Windows
  (`WinError 206`) et la revue LLM était indisponible. Un moteur déjà installé doit être réinstallé
  pour en profiter.

---

## [0.1.0] - 2026-07-02

### Ajouté

- Création de l'architecture initiale du registre de skills IA
- Structure de dossiers : `skills/`, `docs/`, `schemas/`, `templates/`, `tools/`
- Schéma JSON de validation des métadonnées (`schemas/skill.schema.json`)
- Template de skill réutilisable (`templates/skill-template/`)
- Skill d'exemple : `skills/shared/development/java-code-review/`
- Documentation principale : `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Documentation technique : `docs/architecture.md`, `docs/conventions.md`, `docs/compatibility.md`, `docs/contributing.md`
- Modèles GitHub : templates d'issues et de pull request
- Fichiers de configuration Git : `.gitignore`, `.editorconfig`, `.gitattributes`
- Licence MIT

[0.1.0]: https://github.com/FTurleque/ai-skills-registry/releases/tag/v0.1.0
