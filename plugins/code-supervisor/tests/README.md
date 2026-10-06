# Tests de caractérisation du superviseur de code

Filet de sécurité pour les refactorisations du moteur. Ces tests ne disent pas que le superviseur a
« raison » : ils disent que **sa sortie n'a pas changé**. Une sortie qui bouge sans qu'on l'ait voulu
fait échouer le test ; une sortie qui bouge volontairement se valide en régénérant la référence.

## Lancer

```bash
python plugins/code-supervisor/tests/run_tests.py                # compare le moteur aux références
python plugins/code-supervisor/tests/run_tests.py --only rules   # une seule suite : hook ou rules
python plugins/code-supervisor/tests/run_tests.py --update       # régénère golden/ après un changement voulu
python plugins/code-supervisor/tests/run_tests.py --script ~/.claude/hooks/supervisor.py   # moteur installé
```

Aucune dépendance en dehors de Python et de `git`. La CI les rejoue sur Linux.

## Deux suites

| Suite | Ce qu'elle exerce | Référence |
|---|---|---|
| `hook` | le hook de bout en bout : charge utile sur stdin, sortie sur stdout, dans des dépôts git jetables | `golden/hook_scenarios.json` |
| `rules` | toutes les règles de détection sur `corpus/` : par ligne, par bloc, par fichier, sécurité, nommage, imports, complexité et bugs par fonction, extraction des fonctions, duplication | `golden/rules.json` |

**`hook`** (24 entrées) : tours de blocage puis libération de l'empreinte anti-boucle, autre session,
événement `SubagentStop`, `stop_hook_active`, `SUPERVISOR_ACTIVE`, agent superviseur, entrée invalide,
transcript avec lignes corrompues, état corrompu, dossier de journal imposé, chemin accentué, `--check`
avec ou sans chemin, `--self-test`, et l'état anti-boucle persisté. La revue par modèle est coupée.

**`rules`** (182 entrées), deux familles :

- `<config>|<sélection>|<fichier>` : `check_lines`, `check_blocks` et `check_file`, avec deux jeux de seuils
  (défauts et seuils bas) et deux sélections de lignes modifiées (toutes, une sur trois) ;
- `extra|<config>|<fichier>` et `duplication|<config>` : sécurité, nommage, imports inutilisés, extraction
  des fonctions (nom, bornes, paramètres, propriétaire, type de retour), complexité et bugs par fonction, et
  duplication, avec les défauts et des seuils de fonction très bas.

Le test échoue aussi si le corpus ne déclenche pas **toutes les règles que le moteur déclare** (71 aujourd'hui,
lues dans les modules de règles) : une règle ajoutée sans cas de corpus fait échouer le test, sauf si elle
figure dans `UNCOVERED_RULES` avec sa raison. Sans cela, une règle qui cesse de se déclencher passerait
inaperçue.

## Le corpus

`corpus/` contient du code **volontairement fautif**, écrit à la main : Java (dont des chemins `test/` et
`cli/`, des `catch` dont le commentaire fait 24 et 25 caractères, de part et d'autre du seuil de
justification), JavaScript, TypeScript, Python (dont des noms de fichiers et de chemins qui changent le
comportement de certaines règles : `tests/`, `scripts/`, `__main__.py`), des espaces en fin de ligne, plus de
cinq nombres magiques dans un même fichier, des marqueurs de suppression cités dans des chaînes.

**Secrets.** Les règles de secrets (clé AWS, clé privée, jeton JWT, jeton Slack ou GitHub) reconnaissent des
formats que le validateur du dépôt et la protection des secrets de GitHub refusent en clair. Leurs valeurs
sont donc **assemblées à l'exécution** à partir de fragments (`rules_corpus.generated_files`), écrites dans
un dossier temporaire, et la référence ne conserve qu'une empreinte de l'extrait de ces fichiers.

Le corpus est autonome : pas de fichier de la bibliothèque standard, pas de `node_modules`. Il est
silencieux pour le superviseur lui-même (`quiet_paths` dans `.claude/supervisor.config.json`), sans quoi
chaque modification du corpus ferait bloquer l'agent.

**Ajouter un cas** : déposer un fichier dans `corpus/`, lancer `--update`, relire le diff de `golden/` : il
doit montrer exactement les constats que l'on attend, et rien d'autre.

## Portabilité des références

Les sorties sont normalisées avant comparaison pour être identiques d'une machine à l'autre : dossier de
travail remplacé par `<work>` (avec des `/`), dates, noms de rapport, fins de ligne. Le JSON du hook est
comparé décodé, pas en texte. Les dépôts de test sont créés avec une configuration git isolée
(`GIT_CONFIG_GLOBAL`), sans conversion de fins de ligne. Les références contiennent des empreintes
(`sha256`, 8 caractères) à la place du texte des correctifs, trop verbeux : un changement de texte reste
détecté, sans noyer le diff.

## Vérifier que les tests voient bien une régression

Un test qui ne détecte rien est pire que pas de test. Pour s'en assurer, copier le moteur, introduire une
modification qui change le comportement (un seuil, un filtre inversé, un drapeau ignoré) et relancer avec
`--script` : le test doit échouer. C'est ainsi que le corpus a été complété : une mutation de seuil de
commentaire de `catch` passait inaperçue tant qu'aucun commentaire ne faisait 24 ou 25 caractères.

## Limites

- Les références figent le comportement actuel, **y compris ses défauts**. Exemple relevé en les écrivant :
  `BUG.DIV_ZERO` ne signale jamais `/ size()`, parce que son expression se termine par `size\(\)\b` et qu'une
  borne de mot ne peut pas suivre une parenthèse fermante. Le corpus contient `divisionBySize` pour que la
  correction de ce défaut se voie dans le diff de la référence.
- La couverture porte sur le déclenchement des règles et la stabilité de leur sortie, pas sur leur
  justesse : un faux positif figé dans la référence n'est pas détecté.
- La revue par modèle (`llm.py`) n'est pas exercée : elle suppose le CLI `claude` authentifié.
