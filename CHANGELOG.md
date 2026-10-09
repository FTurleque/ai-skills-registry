# Changelog

Toutes les modifications notables de ce dépôt sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet respecte le [Versionnement Sémantique](https://semver.org/lang/fr/).

---

## [Non publié]

### Ajouté — skill `audit-application` 1.0.0 (expérimental)

Skill d'audit de code complet d'une application : six axes (architecture, qualité, sécurité, tests, performance,
dépendances et exploitation) audités en parallèle, un rapport versionné sous `docs/audit/<date>/`, un découpage
des corrections en sprints dont l'ordre est vérifié par script, et un artefact de synthèse (notes par axe,
diagramme d'architecture, feuille de route des sprints, tableau filtrable). Trois profils : complet, sécurité,
rapide. Ne modifie pas le code applicatif pendant l'audit ; n'utilise pas de serveur d'indexation de code tiers
sauf demande explicite. Surfaces déclarées : `claude-code` et `claude-desktop`.

### Corrigé — `code-supervisor` 1.2.0 : périmètre, revue par modèle muette et faux positifs

Constats faits en relisant les rapports d'une longue session : le même lot de constats revenait à chaque tour.

- **Périmètre.** Les fichiers lus dans le transcript (quatre mille dernières lignes) étaient relus en entier à
  chaque passe, même déjà commités et inchangés : le rapport portait sur toute la session, pas sur le tour.
  Dans un dépôt git, ils ne comptent plus ; la base est le commit de la dernière passe (ou, à la première, le
  dernier commit antérieur au début du transcript), et un fichier dont le contenu a déjà été relu sans blocage
  n'est pas relu. Un fichier qui portait un point bloquant l'est de nouveau (l'anti-boucle est inchangé).
- **Revue par modèle muette.** Quand `claude -p` répondait `is_error` (par exemple « OAuth session expired »),
  le verdict disait « sans résultat exploitable » et le message annonçait « aucun problème bloquant » comme si
  la relecture avait eu lieu. La cause est maintenant reprise telle quelle, et le verdict dit « analyse
  statique seule ».
- **`BUG.CATCH_SILENT_RETURN`.** N'est plus signalé pour un `catch` qui fait autre chose que sortir (il compte,
  enregistre ou lit la cause), qui porte un commentaire d'au moins 25 caractères, ou qui renvoie un texte.
- **`BUG.THREAD_SLEEP`.** Un `sleep` dans une boucle bornée par une échéance (`deadline`, `timeout`, `nanoTime`…)
  est le polling que la règle recommande : il n'est plus signalé.
- **`NAM.VAGUE_VARIABLE` et `NAM.VAGUE_PARAM`.** `temp` et `tmp` ne sont plus signalés quand ils nomment un
  `@TempDir`.
- **`DUP.BLOCK`.** Les déclarations de champs de même forme (`private final X y;`) ne comptent plus comme du code
  dupliqué.
- Tests : 6 scénarios de hook (périmètre, passes successives, revue en échec), 5 fichiers de corpus et 1 scénario de
  duplication ajoutés ; la référence passe de 24 à 30 entrées de hook et de 582 à 621 entrées de règles. Rejoués contre le moteur
  1.1.0, ils échouent (14 entrées de règles, 5 de hook) : ils exercent bien les changements.

### Ajouté — skill `code-to-openspec` 1.0.0 (expérimental)

Skill de rétro-ingénierie : analyse une application existante à partir de son code et prépare des changements
OpenSpec traçables (constat → changement → exigence → scénario → tâche → validation). Trois modes (audit global,
analyse ciblée, reprise), sept qualifications de preuve (comportement observé, exigence documentée ou proposée,
défaut confirmé, risque potentiel, amélioration proposée, décision à clarifier), par défaut aucune modification
du code de production. Conçu pour être distribué à d'autres projets : indépendant du langage, de l'IDE et de
l'OS, MCP d'IDE facultatif, aucune dépendance au dépôt qui l'héberge.

- Formats OpenSpec vérifiés avec le CLI 1.14.1 (schéma `spec-driven`), dont un changement d'exemple dont la
  structure passe `openspec validate --strict`. Le CLI reste la référence au moment de l'emploi.
- `resources/audit_tool.py` (Python 3.8+, facultatif) : `check`, `snapshot`, `drift`, `next-id`, contrôles
  déterministes des constats et de la traçabilité. 32 tests (`resources/tests/`) ; une mutation de la logique de contrôle
  a révélé un test dépendant de la plateforme (fins de ligne), corrigé.
- **Pas encore utilisé en conditions réelles.** Seulement joué par des agents Claude qui lisaient ses instructions
  sur quatre petits projets de test (sans OpenSpec, avec OpenSpec et bug ciblé, monorepo à build bloqué, reprise
  d'audit) ; leurs affirmations ont été recontrôlées de l'extérieur, mais ni le déclenchement par la description ni
  l'usage par une personne n'ont été observés. Ce qui reste à faire (grand dépôt réel, MCP d'IDE disponible,
  autres schémas OpenSpec) est listé dans `examples/validation-scenarios.md`.
- Surfaces déclarées : `claude-code` (essayée sous forme de lecture par des agents dans l'onglet Code de
  l'application de bureau) et `claude-desktop` (mode Cowork : non essayé).

### Modifié — `install.py` découpé, testé et corrigé (ticket #29)

`install.py` n'avait aucun test alors qu'il écrit dans le `settings.json` de l'utilisateur. Une suite de 22
scénarios (`tests/install_scenarios.py`, référence `golden/install_scenarios.json`) le couvre maintenant :
installation neuve, de projet, réinstallation, ancien hook, désinstallation, et réglages hostiles. Écrite
d'abord, référencée avec l'ancien installeur, elle a révélé des défauts réels :

- **Désinstallation incomplète** : quand notre hook partageait un groupe avec un autre hook, `remove_hooks` ne
  signalait aucun changement. Les fichiers étaient supprimés, mais `settings.json` gardait un hook vers un
  script qui n'existe plus. Le hook est maintenant retiré, et le groupe garde les autres.
- **Plantages sur des réglages mal formés** : un `settings.json` qui n'est pas un objet, un événement qui n'est
  pas une liste ou un groupe qui n'est pas un objet faisaient échouer l'installation ou la désinstallation avec
  un `AttributeError`. Les deux premiers sont refusés proprement (code 2, message), les groupes et handlers
  étrangers sont laissés tels quels.
- **« Rien n'a été modifié » était faux** : l'installeur copiait tous les fichiers avant de lire `settings.json`.
  Il le lit maintenant d'abord ; un fichier refusé ne laisse plus rien derrière lui.
- **Un groupe vide qui n'était pas à nous** était supprimé par la désinstallation : il est maintenant laissé.
- **Console** : l'auto-test s'affichait `OK ? toutes…` (le tiret long était remplacé par un « ? » même quand
  la console sait l'afficher). La sortie remplace désormais seulement ce qu'elle ne sait pas afficher.

Le découpage lui-même (`merge_hooks`, `remove_hooks`, `main` en fonctions courtes, un point de sortie `say`,
`HOOK_TIMEOUT_SECONDS`, des noms explicites) a été validé d'abord à référence identique, puis les corrections
ci-dessus dans un second temps, avec le diff de la référence relu : 17 scénarios sur 22 changent, tous
attendus. `install.py` passe de 27 constats du superviseur à 0.

Par mutation, 39 modifications de l'installeur sur 40 sont détectées ; la dernière (copier tous les fichiers du
moteur et non les seuls `.py`) ne change rien sur un arbre sans `__pycache__`. Les `except Exception` de
`run_git` et de `_relativize` sont restreints aux pannes attendues, avec un contrôle de l'auto-test.

Un incident à retenir : une première série de mutations a fait viser le vrai `~/.claude` à l'installeur (la
mutation ignorait `CLAUDE_CONFIG_DIR`) et les scénarios de désinstallation ont supprimé l'installation de la
personne qui lançait les tests. L'installeur tourne désormais avec un `HOME` et un `USERPROFILE` jetables.

### Modifié — `shell=True` des `external_tools` conservé, décision documentée et vérifiée (ticket #26)

Décision : **on garde le shell**. La commande est écrite par l'utilisateur dans sa propre configuration (même
confiance que le hook de `settings.json`), et une liste d'arguments n'apporterait rien là où le risque existe.
Mesuré sous Windows avec un script `.cmd` inoffensif : `npx` et `mvn`, les exemples du README, sont des scripts
`.cmd` que `cmd.exe` interprète même sans shell. Un nom de fichier `a&ver` y exécute `ver`, `%COMSPEC%` y est
développé, un guillemet dans le nom casse la ligne. Le rejet des noms dangereux de `quote_path` reste donc
nécessaire dans les deux cas, et passer en liste aurait supprimé `&&`, les redirections et les variables des
commandes déjà déclarées, sans rien gagner.

À la place d'un argument d'autorité, un contrôle exécutable : l'auto-test lance `run_external_tools` avec huit
noms de fichiers (espace, `&`, `$(…)`, accent grave, `;`, `$HOME`, apostrophe) vers un programme qui enregistre
ses arguments, et exige que les noms acceptés arrivent intacts, que les noms refusés ne soient pas lancés et
qu'aucune commande ne s'exécute. Sous Windows, sept noms arrivent intacts et `a&b.py` est refusé. Une
mutation qui cesse de citer les noms (`a&b.py` exécute `b.py`) est détectée par ce contrôle seul ; le contrôle
existant sur `quote_path` ne la voyait pas. Le constat « appel système avec `shell=True` » du superviseur reste
affiché : il est maintenant documenté dans `engine.run_external_tools`, dans le README et dans
`supervisor.config.json`. Aucun changement de comportement du moteur. Un moteur déjà installé doit être
réinstallé pour profiter du contrôle.

### Corrigé — extraction des fonctions Kotlin, Scala et Go, et `BUG.DIV_ZERO` (ticket #28)

- **Corps-expression** (`fun twice(x: Int) = x * 2` en Kotlin, `def inline(x: Int) = x + 1` en Scala) : la
  fonction adoptait l'accolade de la fonction suivante, donc des bornes, une complexité et une longueur
  fausses, et une fonction à corps-expression en fin de fichier n'était pas détectée du tout. Elle est
  maintenant comptée sur sa ligne, comme les fonctions à `=>`. `= {` (corps à bloc, Scala) et les déclarations
  C++ `= delete;`, `= default;`, `= 0;` ne changent pas.
- **Méthodes Go** (`func (s *Server) Name()`) : elles étaient lues comme une fonction nommée `func`. Elles
  prennent leur vrai nom, et le type du receveur (`Server`, `Stack` pour `*Stack[T]`) sert de propriétaire.
  Conséquence : les règles de nommage s'appliquent enfin à ces méthodes (`Server.Handle` reçoit
  `NAM.VAGUE_VERB`).
- **`BUG.DIV_ZERO`** signale maintenant `/ values.size()`, `/ items.length`, `/ text.length()` et
  `/ stats.summary.count`, pas seulement les diviseurs nus. Pour que l'élargissement ne bloque pas l'agent à
  tort, un test de valeur sur le diviseur lui-même vaut garde (`if count:`, `if (!items.length) return`,
  `a / n if n else 0`) : ce faux positif existait déjà pour les diviseurs nus (`if length:` avant `/ length`
  dans `difflib.py`) et disparaît aussi.

Méthode du ticket : cas de corpus d'abord (Kotlin, Scala, Go, C++, C#, Java, Python et JavaScript), référence
enregistrée avec l'ancien moteur, correction, puis diff de la référence relu : 20 entrées sur 8 fichiers, rien
d'autre. Les fixtures sont identiques. Sur 400 fichiers de la bibliothèque standard Python, l'élargissement
ne produit aucun nouveau constat et en retire un (le faux positif de `difflib.py`). Par mutation, 26
modifications du nouveau code sur 26 sont détectées ; deux ne l'étaient pas d'abord, faute de cas (`=>` suivi
d'une accolade sur plusieurs lignes en C#, et `;` sur une ligne ultérieure d'un fichier Kotlin) et ont leur cas
maintenant. Un moteur déjà installé doit être réinstallé.

### Modifié — parcours par ligne factorisé entre `rules_bugs` et `rules_security` (ticket #27)

Les deux `_line_findings` partageaient la même structure : filtre de langage, choix de la ligne brute ou
nettoyée, exception propre à la règle, construction du constat. Elle vit maintenant dans
`supervisor/line_rules.py` (`LineRules`, `line_findings`) ; chaque module ne déclare plus que sa catégorie,
sa gravité et ses exceptions. Une ligne voyage dans un objet `Line` (numéro, brut, nettoyé, épuré) plutôt que
dans quatre paramètres : sans lui, la factorisation ajoutait deux constats « 6 paramètres ». Le MAJOR « duplication » entre les deux fichiers disparaît, sans toucher au
seuil `duplication_lines`. **Aucun changement de comportement** : 24 scénarios du hook et 526 entrées de
règles identiques, analyse complète du corpus et des fixtures identique avant/après (396 et 38 constats).

Par mutation, 14 modifications du nouveau code sur 14 sont détectées. Une première série en avait laissé
passer une, **sans rapport avec le découpage** : `_is_false_match` lit la ligne brute (un mot de contexte ou
`safe_eval` dans un commentaire de fin de ligne compte), et aucun cas du corpus ne le distinguait de la ligne
nettoyée. Deux lignes de `py/security_filters.py` comblent le trou ; la référence, régénérée avec l'ancien
moteur, ne gagne que les constats correspondants (et le décalage de la ligne trop longue qui suit).
Un moteur déjà installé doit être réinstallé.

### Modifié — `code-supervisor` passe en 1.1.0 (clôture du ticket #11)

Version mineure : le comportement de `external_tools` change (la configuration d'un projet ne peut plus
déclarer de commande, de CLI de revue ni de dossier de journal, voir « Sécurité » plus bas). Elle regroupe
aussi les corrections d'encodage, de quoting et de règles, le découpage des fonctions complexes et les tests
de caractérisation. Un moteur déjà installé doit être réinstallé (`install.py`).

Restent ouverts à dessein : `shell=True` dans `engine.run_external_tools` (nécessaire pour `npx` ou `mvn`,
quoting sûr), la structure commune de `rules_bugs._line_findings` et `rules_security._line_findings`, le
faux positif documenté de `source.run_git`, les défauts d'extraction figés par les références (fonctions
Kotlin à corps d'expression, receveur de méthode Go), `/ liste.size()` non signalé par `BUG.DIV_ZERO`, et les
points MINOR de style.

### Modifié — `rules_duplication.check` et `_corpus_files` découpées (ticket #11)

`check` (complexité 22) devient `_target_files`, `_duplicated_pair`, `_duplicate_finding`, `_report` et un
`check` de quinze lignes ; `_corpus_files` (17) devient `_reference_path`, `_collect_candidates` et un
`_corpus_files` plus court. Le parcours de `os.walk` et l'ordre des vérifications de limite sont conservés à
l'identique. **Aucun changement de comportement** : référence produite par l'ancien moteur (526 entrées),
24 scénarios du hook, analyse complète du corpus et des fixtures (392 et 38 constats) identiques.

Même méthode, même constat : **5 mutations de l'ancien code sur 15 seulement étaient détectées**, et pour une
raison de fond. La référence appelait `check` en passant tout le corpus comme « modifié » : `_corpus_files`
n'avait alors rien à lire, et la recherche dans le reste du dépôt n'était jamais exercée. La suite compte
maintenant 16 scénarios de duplication (fichier seul, deux fichiers, même fichier, dossier exclu, motif exclu,
autre extension, autre dossier de premier niveau, fichier à la racine, test, YAML, limites du nombre de
fichiers de référence) sur quatre configurations, et le corpus gagne les fichiers correspondants. Sur le code
découpé : 14 mutations non équivalentes sur 14 détectées ; les quatre autres sont équivalentes (élagage des
dossiers exclus déjà couvert par `is_excluded`, comparaison d'un fichier à lui-même, emplacement « hors fichiers
modifiés », racine absente) ainsi que la normalisation des séparateurs, qui ne change rien sous Windows.

La duplication, comme l'extraction des fonctions, n'était donc couverte qu'en apparence. Un moteur déjà
installé doit être réinstallé.

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
