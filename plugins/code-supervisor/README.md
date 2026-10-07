# Code Supervisor

Un garde-fou qui se declenche **tout seul, dans n'importe quel projet**, des qu'un agent a fini
d'ecrire du code. Il relit ce qui vient d'etre modifie et, si quelque chose cloche, **renvoie
l'agent corriger avant qu'il ne rende la main**.

---

## Ce que c'est, exactement

**Ce n'est pas une skill : c'est un plugin.** Il vit sous `plugins/`, et le registre separe les
deux pour cette raison : une skill est un fichier d'instructions que Claude lit quand il en a
besoin, un plugin est un paquet qui branche du code sur des evenements de l'outil.

Un plugin Claude Code est un paquet qui peut livrer plusieurs sortes de composants. Celui-ci en
livre trois, plus son moteur :

| Fichier | Ce que c'est | Qui le declenche |
|---|---|---|
| `hooks/hooks.json` | **le coeur** — la partie automatique | Claude Code lui-meme, a la fin de chaque reponse d'agent (`Stop`) et de chaque sous-agent (`SubagentStop`) |
| `agents/code-supervisor.md` | un sous-agent de relecture | vous, quand vous l'appelez |
| `SKILL.md` | la procedure de relecture, en instructions | vous via `/code-supervisor`, ou Claude quand la tache s'y prete |
| `resources/` | le moteur Python : analyse statique, relecture par modele, rapport | les trois composants ci-dessus |

Le `SKILL.md` est la porte d'entree manuelle : il decrit la procedure de relecture, pour quand vous
voulez un verdict a la demande. Mais ce n'est pas lui qui fait tourner le superviseur : c'est le
hook.

Specifique a Claude Code, donc, et non portable vers un autre assistant : les hooks et les
sous-agents sont des mecanismes propres a l'outil.

---

## Comment ca se branche

1. Vous lancez les deux commandes d'installation ci-dessous.
2. Claude Code copie le plugin dans son propre dossier de plugins, lit `hooks/hooks.json`, et
   enregistre deux abonnements : « a la fin d'une reponse d'agent, executer
   `python <plugin>/resources/supervisor.py` ».
3. A partir de la, plus rien a faire. Dans **tous** vos projets, chaque fois qu'un agent finit
   d'ecrire du code et s'apprete a rendre la main, Claude Code lance le script, lui passe le
   contexte de la session sur l'entree standard, et attend sa reponse.
4. Si le script repond « bloque », l'agent ne rend pas la main : il recoit la liste des corrections
   a faire et repart au travail. Sinon, les constats non bloquants sont injectes dans son contexte
   et un rapport est ecrit sur disque.

Votre `settings.json` n'est pas modifie : c'est le plugin qui porte la declaration des hooks.
Pour verifier que tout est en place : `claude plugin list` puis `claude plugin details
code-supervisor`.

### Les trois usages, par ordre d'importance

| Usage | Ce que vous faites | Ce que vous voyez |
|---|---|---|
| **Passif** (la raison d'etre) | rien | une ligne d'etat : « Superviseur de code : 3 fichier(s) relu(s), 1 critical — agent renvoye en correction », et l'agent qui corrige de lui-meme |
| **A la demande** | `@code-supervisor:code-supervisor relis mes modifications` | le verdict dans la conversation |
| **En ligne de commande** | `python <plugin>/resources/supervisor.py --check` | le rapport sur la sortie standard, utile avant un commit |

---

## Ce qu'il surveille

| Domaine | Exemples de controles |
|---|---|
| Securite | secrets en dur, injection SQL ou de commande, deserialisation non sure, crypto faible, TLS desactive, secrets dans les journaux, XXE, CSRF desactive |
| Bugs introduits | exception avalee, comparaison de chaines par reference, ressource non fermee, modification d'une collection pendant son parcours, `Optional.get()` sans garde, division par zero, montant en `double`, formateur de date statique, comparaison a NaN |
| Duplication | bloc reecrit ailleurs dans le diff **ou deja present dans le depot** |
| Complexite | complexite cyclomatique, longueur de methode et de fichier, imbrication, nombre de parametres, conditions a rallonge |
| Nommage | noms vides de sens (`data`, `tmp`, `truc`), abreviations, noms numerotes, `get*` qui ecrit ou ne retourne rien, verbe passe-partout (`doStuff`), casse non conforme |
| Conventions | imports generiques ou inutilises, code commente, nombres magiques, indentation mixte, TODO laisses, **neutralisation d'un controle qualite** (`@SuppressWarnings`, `// NOSONAR`, `# noqa`, test desactive) |

Analyse structurelle : Java, Kotlin, Scala, JS/TS, C#, Go, Rust, Swift, C/C++, PHP, Groovy, Dart,
Python. Les autres fichiers reconnus passent par les controles de securite et de forme.

---

## Comment ca marche

```text
agent termine sa reponse
        |
        v
hook Stop / SubagentStop  -->  resources/supervisor.py
                                 |
                                 |- perimetre : git status + commits depuis la derniere passe de la session
                                 |- lignes modifiees : git diff -U0
                                 |- couche 1 : analyse statique portable, sans dependance
                                 |- couche 2 : relecture par modele (claude -p, hooks desactives)
                                 v
                        CRITICAL ?  --oui-->  decision "block" + consignes  -->  l'agent corrige
                             |
                             non
                             v
                      avertissement non bloquant dans le contexte + rapport ecrit
```

Deux couches, parce qu'elles ne savent pas les memes choses. La couche statique est deterministe
et gratuite : elle mesure ce qui se mesure. La couche modele juge ce qui ne se mesure pas — est-ce
que ce nom decrit vraiment la chose, est-ce que ce diff casse un appelant, est-ce que ca reinvente
ce qui existe deja dans le depot.

---

## Installation

Deux voies. La voie plugin est la voie normale ; l'installation manuelle existe pour les
environnements ou les plugins ne sont pas disponibles.

### Voie 1 — plugin Claude Code (recommandee)

```bash
# depuis GitHub
claude plugin marketplace add FTurleque/ai-toolkit-registry
claude plugin install code-supervisor@ai-toolkit-registry

# ou depuis un clone local, pour tester avant publication
claude plugin marketplace add ./ai-toolkit-registry
claude plugin install code-supervisor@ai-toolkit-registry
```

Verifier :

```bash
claude plugin list
claude plugin details code-supervisor
```

Mettre a jour, retirer :

```bash
claude plugin update code-supervisor@ai-toolkit-registry
claude plugin uninstall code-supervisor@ai-toolkit-registry
```

Rien n'est ecrit dans votre `settings.json` : les hooks sont declares par le plugin, dans
`hooks/hooks.json`.

**Prerequis** : `python` doit etre resolvable dans le PATH. Le hook est declare en forme exec
(`args`), ce qui evite les problemes de quoting sous Windows mais interdit un repli automatique
vers `python3`. Sur une distribution Linux ou seul `python3` existe, installer
`python-is-python3` ou utiliser l'installation manuelle, qui detecte l'interpreteur.

### Voie 2 — installation manuelle dans `~/.claude`

```powershell
# Windows
cd plugins\code-supervisor\resources
.\install.ps1
```

```bash
# Linux / macOS
cd plugins/code-supervisor/resources
./install.sh
```

L'installateur copie le moteur dans `~/.claude/`, declare les hooks `Stop` et `SubagentStop` dans
`~/.claude/settings.json` **sans toucher a ce qui s'y trouve deja** (sauvegarde en
`settings.json.bak`), puis lance l'auto-test. Relancer l'installateur est sans danger.

```bash
python install.py --project /chemin/du/projet   # limiter a un projet
./install.sh --uninstall                        # desinstaller
```

---

## Usage manuel

```bash
python <racine>/resources/supervisor.py --check                  # relit les fichiers modifies
python <racine>/resources/supervisor.py --check --llm            # avec la relecture par modele
python <racine>/resources/supervisor.py --check src/Foo.java     # un fichier precis
python <racine>/resources/supervisor.py --self-test              # verifie le moteur
```

`<racine>` est le dossier du plugin installe, ou `~/.claude` apres une installation manuelle.

Depuis une session Claude Code :

- skill : `/code-supervisor` — la procedure de relecture complete
- sous-agent, installation plugin : `@code-supervisor:code-supervisor relis mes modifications`
- sous-agent, installation manuelle : `@code-supervisor relis mes modifications`

---

## Reglages

Fusion du plus general au plus specifique : valeurs du code, `supervisor.config.json` livre a cote
du moteur, `~/.claude/supervisor.config.json`, puis `<projet>/.claude/supervisor.config.json`
(ou `<projet>/.supervisor.json`).

> **Securite.** Le depot supervise n'est pas une source de confiance : un projet clone peut ne pas
> etre le votre. La configuration du **projet** ne peut donc pas fixer `external_tools`, `llm.cli`
> ni `log_dir` (ils designent un programme a lancer ou un emplacement d'ecriture). Ces cles sont
> ignorees, avec un avertissement sur la sortie d'erreur ; declarez-les dans
> `~/.claude/supervisor.config.json` si c'est voulu. Tous les autres reglages restent surchargeables
> projet par projet.
>
> **Pourquoi un shell pour `external_tools`.** La commande est la votre, ecrite dans votre configuration :
> meme confiance que la commande du hook dans `settings.json`. Elle est lancee par un shell (`&&`, redirections
> et variables fonctionnent), et le moteur ne change pas cela a dessein : sous Windows, `npx` et `mvn` sont des
> scripts `.cmd` que `cmd.exe` interprete de toute facon, avec ou sans liste d'arguments (mesure : un nom
> `a&ver` y execute `ver`). Ce qui vient du depot supervise, les noms de fichiers, est cite par le moteur ;
> sous Windows, un nom contenant `"%^&|<>!` ou un caractere de controle n'est pas passe a l'outil, et
> l'auto-test verifie de bout en bout qu'aucun nom de fichier n'execute de commande.

| Cle | Effet |
|---|---|
| `block_on_severity` | severites qui renvoient l'agent au travail. `["CRITICAL"]` par defaut ; `["CRITICAL","MAJOR"]` pour serrer, `[]` pour un mode purement consultatif |
| `never_block_categories` | categories qui n'arretent jamais l'agent, ex. `["nommage","convention"]` |
| `max_block_rounds` | nombre maximal de renvois pour un **meme** lot de problemes (3). Au-dela, avertissement sans blocage |
| `thresholds` | tous les seuils : complexite, longueur, parametres, imbrication, taille du bloc duplique |
| `llm.enabled`, `llm.model` | couche modele : la couper, ou changer de modele |
| `external_tools` | outils a appeler (ruff, eslint, checkstyle). **Vide par defaut** : rien ne s'execute sans declaration explicite, aucun build ni CI n'est declenche par surprise. **Honore uniquement depuis la configuration utilisateur ou celle du moteur, jamais depuis un projet.** Des exemples prets a copier sont dans le fichier |
| `quiet_paths` | chemins ou le superviseur se tait |
| `enabled` | `false` pour tout desactiver sans desinstaller |

Variables d'environnement : `SUPERVISOR_NO_LLM=1` coupe la couche modele pour une execution,
`SUPERVISOR_LOG_DIR` deplace les rapports, `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` releve le plafond de
blocages de Claude Code (8 par defaut).

---

## Garde-fous

- **Pas de boucle.** Le drapeau `stop_hook_active` est respecte, et un meme lot de problemes ne
  peut renvoyer l'agent que `max_block_rounds` fois : ensuite il est signale sans blocage.
- **Pas de recursion.** Le relecteur est lance avec les hooks desactives et une variable de garde.
- **Pas de jugement sur du code non touche.** Seules les lignes du diff sont evaluees, plus les
  fonctions qui les contiennent. Un fichier nouveau est lu en entier.
- **Pas de relecture du deja relu.** Le superviseur retient, par session, le commit de la derniere
  passe et l'empreinte du contenu des fichiers relus sans blocage : un fichier inchange depuis, commite
  entre-temps ou non, n'est pas relu. Un fichier qui portait un point bloquant l'est a la passe suivante.
  A la premiere passe d'une session, la base est le dernier commit anterieur au debut du transcript.
- **Une revue par modele absente se voit.** Si `claude -p` echoue (session expiree, quota, modele refuse),
  le message du CLI est repris dans le verdict, qui se dit « analyse statique seule » au lieu d'annoncer
  une relecture complete. Pour une session expiree : `claude` puis `/login` dans un terminal.
- **Pas de contournement.** Neutraliser un avertissement ou desactiver un test pour faire taire un
  controle est lui-meme signale comme un defaut.
- **Budget borne.** 45 s d'analyse statique par defaut, 60 fichiers au plus, corpus de duplication
  plafonne. Au-dela, le superviseur rend ce qu'il a.
- **Degradation propre.** Pas de depot git, pas de CLI `claude`, fichier illisible, outil absent :
  il fait ce qu'il peut et ne bloque jamais la session sur une erreur interne.

---

## Rapports

Chaque passage ecrit `<projet>/docs/rapport-supervisor/rapport-<horodatage>.md` : constats par
categorie, fichiers relus, verdict. L'etat anti-boucle de la session est dans
`state-<session>.json`. Le dossier contient son propre `.gitignore` (`*`) : les rapports ne sont
jamais commites et le `.gitignore` du projet supervise reste intact.

---

## Verifications effectuees

| Verification | Resultat |
|---|---|
| Auto-test sur fixtures fautives | les 11 regles attendues se declenchent |
| Bruit sur 10 fichiers reels d'un projet Java (~2 000 lignes) | 21 constats, 0 critical, 4 major tous plausibles |
| Anti-boucle sur 5 passes du meme lot | blocage 3 fois, puis avertissement, stable |
| Gardes `stop_hook_active`, anti-recursion, hors depot git, auto-supervision | sortie vide, aucun effet |
| Chaine de bout en bout avec la couche modele | validee avec une CLI factice, non exercee contre le modele reel |

---

## Structure

```text
code-supervisor/
├── .claude-plugin/plugin.json   manifeste du plugin
├── hooks/hooks.json             declaration des hooks Stop et SubagentStop
├── agents/code-supervisor.md    sous-agent de relecture a la demande
├── SKILL.md                     instructions du skill (registre + skill du plugin)
├── metadata.yaml                metadonnees du registre
├── README.md                    ce fichier
├── examples/example.md          un diff fautif, le verdict, le message a l'agent
├── tests/                       tests de caracterisation du moteur (voir tests/README.md)
└── resources/
    ├── supervisor.py            point d'entree : place le moteur sur le chemin d'import et delegue
    ├── supervisor/              moteur
    │   ├── runner.py            hook, mode manuel, auto-test, etat anti-boucle
    │   ├── model.py             constat, severites, deduplication
    │   ├── source.py            langages, nettoyage, extraction des fonctions, diff git
    │   ├── line_rules.py        parcours par ligne commun aux regles de securite et de bugs
    │   ├── rules_security.py    secrets, injections, crypto, configuration dangereuse
    │   ├── rules_bugs.py        bugs probables, par ligne, par bloc, par fonction
    │   ├── rules_quality.py     complexite, taille, imbrication, conventions de forme
    │   ├── rules_naming.py      pertinence des noms
    │   ├── rules_duplication.py empreintes de fenetres de lignes normalisees
    │   ├── engine.py            orchestration, outils externes, verdict
    │   ├── llm.py               relecture par modele
    │   └── report.py            message a l'agent, message utilisateur, rapport
    ├── supervisor.config.json   reglages par defaut, commentes
    ├── fixtures/                code volontairement fautif, pour l'auto-test
    └── install.py / .ps1 / .sh  installation manuelle, mise a jour, desinstallation
```

---

## Voir aussi

- [`java-code-review`](../../skills/development/java-code-review/README.md) — grille de revue Java
  pensee pour une relecture humaine exhaustive. Complementaire : ce skill-ci cible le diff d'une
  session agent, celui-la une revue de fond.
