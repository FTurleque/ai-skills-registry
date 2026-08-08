---
name: generate-windows-exe
displayName: Generate Windows Executable
description: Empaquette une application en executable Windows (.exe) via Inno Setup ou jpackage, avec un driver reproductible.
version: 1.0.0
status: stable
category: development
tags:
  - packaging
  - windows
  - exe
  - inno-setup
  - jpackage
  - release
  - node
  - java
compatibility:
  - generic
  - github-copilot
  - claude-code
authors:
  - Fabrice Turleque
license: MIT
---

# Objectif

Produire un **executable Windows (`.exe`)** a partir d'une application, de facon
reproductible et verifiable. Deux recettes sont couvertes, chacune eprouvee sur
un projet reel :

| Recette | Produit | Outil | Origine du pattern |
|---------|---------|-------|--------------------|
| **A. Installateur** | `app-setup.exe` (assistant + desinstalleur) | Inno Setup (`ISCC.exe`) | `mcp-search-net` (app Node/TypeScript) |
| **B. Lanceur natif** | `app.exe` (binaire autonome) | `jpackage` (fourni avec le JDK) | `nexus-context-engine` (app Java) |

La recette **A** empaquete **n'importe quel dossier** (Node, .NET, binaire, scripts...)
grace au driver [`resources/build-exe.ps1`](resources/build-exe.ps1). C'est le
chemin principal de ce skill.

> Les commandes de ce document ont ete executees sous Windows 10, PowerShell 7,
> avec Node 24.18.0, JDK 24.0.1 et Inno Setup 7.0.2. Chaque bloc a reellement
> produit puis lance un `.exe`.

# Cas d'utilisation

- Livrer une application Windows a un utilisateur final sous forme de `.exe`
- Automatiser la generation d'un installateur dans un pipeline de release
- Transformer un dossier de build (app + runtime) en installateur unique
- Produire un lanceur natif Windows pour une application Java sans exiger un JRE

# Entrees attendues

- **Payload** : le dossier a empaqueter (build compile + fichiers d'accompagnement).
  Pour une app Node, c'est le dossier `build/` + le runtime Node embarque + la config.
- **Nom + version** : nom court (kebab-case) et version SemVer (ex. `1.0.0`, `1.2.3-rc1`).
- **Editeur** (optionnel) : nom affiche dans les proprietes du `.exe`.

# Prerequis

Verifier la chaine d'outils (commandes reellement executees) :

```bash
node --version      # v24.18.0 (recette A si app Node ; non requis pour l'empaquetage lui-meme)
java -version       # openjdk 24.0.1 (recette B)
```

Installer **Inno Setup** (recette A). `ISCC.exe` est le compilateur ligne de commande :

```bash
winget install --id JRSoftware.InnoSetup
```

Le driver auto-detecte `ISCC.exe` dans le `PATH`, dans
`%LOCALAPPDATA%\Programs\Inno Setup 7|6\`, dans `Program Files\Inno Setup 7|6\`
et dans le dossier Chocolatey. Aucune configuration de chemin n'est necessaire
si Inno Setup est installe normalement.

# Recette A — Installateur `.exe` (chemin principal)

Le driver [`resources/build-exe.ps1`](resources/build-exe.ps1) genere un script
Inno Setup depuis [`resources/installer.iss.template`](resources/installer.iss.template)
(substitution de jetons `@@...@@`), compile l'installateur et calcule son SHA-256.

## 1. Preparer un payload

Tout dossier non vide convient. Exemple minimal :

```bash
mkdir -p payload/bin
printf '@echo off\r\necho Hello from demo-app!\r\n' > payload/bin/demo-app.cmd
printf 'demo-app 1.0.0\r\n' > payload/README.txt
```

## 2. Generer le `.exe`

```powershell
./skills/shared/development/generate-windows-exe/resources/build-exe.ps1 `
  -PayloadDir ./payload `
  -AppName demo-app `
  -Version 1.0.0 `
  -AppPublisher "Fabrice Turleque" `
  -OutputDir ./dist
```

Sortie observee :

```
EXE GENERE AVEC SUCCES
Setup    : ...\dist\demo-app-1.0.0-windows-x64-setup.exe
SHA-256  : f1eed147bba323fed027dba8743073368edc60b152d6622cd1d070e78df0add8
AppId    : {{C558494D-C533-87EE-E1D5-8B802F00E837}
Inno     : ...\Inno Setup 7\ISCC.exe
```

Le driver ecrit `dist\<app>-<version>-windows-x64-setup.exe` et son `.sha256`.

## 3. Verifier le `.exe` produit

Confirmer que c'est un PE Windows valide avec les bonnes metadonnees :

```powershell
$exe = "./dist/demo-app-1.0.0-windows-x64-setup.exe"
$bytes = [System.IO.File]::ReadAllBytes($exe)
$magic = -join ($bytes[0..1] | ForEach-Object { [char]$_ })   # doit valoir "MZ"
"$magic  $((Get-Item $exe).VersionInfo.ProductName) $((Get-Item $exe).VersionInfo.ProductVersion)"
```

## 4. Prouver l'installation (silencieuse, sans admin)

Le modele installe dans `%LOCALAPPDATA%` (`PrivilegesRequired=lowest`), donc
l'installation silencieuse ne demande aucune elevation. Piloter l'installateur
avec `Start-Process` et un **tableau d'arguments** (ne pas passer les commutateurs
`/VERYSILENT` dans une chaine unique — voir Gotchas) :

```powershell
$exe = "./dist/demo-app-1.0.0-windows-x64-setup.exe"
$target = "./installed"
$args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$target","/LOG=install.log")
$p = Start-Process -FilePath $exe -ArgumentList $args -Wait -PassThru
"Exit code : $($p.ExitCode)"                 # 0 attendu
& "$target/bin/demo-app.cmd"                  # -> Hello from demo-app!
```

L'installateur depose le payload + un desinstalleur `unins000.exe` dans `$target`.

# Recette B — Lanceur natif `.exe` avec jpackage (Java)

`jpackage` est fourni avec le JDK (17+). Le type `app-image` produit un
lanceur `.exe` **sans** dependance a WiX/Inno Setup. Depuis un JAR executable
(Main-Class dans le manifeste) :

```powershell
# input/ contient app.jar (un fat-jar fonctionne aussi)
jpackage --type app-image --name demo-java-cli `
  --input ./input --main-jar app.jar --main-class Main `
  --win-console `
  --dest ./out
& "./out/demo-java-cli/demo-java-cli.exe"     # -> Hello from ...
```

`--win-console` est **obligatoire pour une application CLI** : sans lui le
lanceur est fenetre (windowed) et n'ecrit rien sur stdout (voir Gotchas).

Pour un vrai fat-jar autonome, `nexus-context-engine` utilise `maven-shade-plugin`
(cf. [`resources/patterns.md`](resources/patterns.md) pour les alternatives
fat-jar + lanceur `.cmd`, GraalVM `native-image`, et Node SEA/`pkg`).

# Contraintes

- **Windows uniquement** : `ISCC.exe` et `jpackage --type app-image` (cible win)
  produisent des binaires Windows et doivent tourner sous Windows.
- **Payload non vide** : le driver echoue si le dossier payload est vide.
- **Ne pas signer** : ce skill ne gere pas la signature Authenticode. Un `.exe`
  non signe declenchera SmartScreen chez l'utilisateur final ; la signature est
  une etape separee (certificat + `signtool`).
- **Pas de chemins absolus** dans les invocations : utiliser des chemins relatifs
  au dossier de travail.

# Processus d'execution

1. Verifier la chaine d'outils (`node`/`java`, `ISCC.exe`).
2. Construire/rassembler le payload (build compile + runtime + config).
3. Recette A : lancer `build-exe.ps1` ; recette B : lancer `jpackage`.
4. Verifier le PE produit (magic `MZ`, metadonnees de version, SHA-256).
5. Prouver le fonctionnement (installation silencieuse, ou execution du lanceur).

# Format de sortie

- Un fichier `.exe` dans `dist/` (recette A) ou `out/<app>/<app>.exe` (recette B).
- Recette A : un fichier `.sha256` accompagnant l'installateur.
- Un compte rendu : chemin du `.exe`, empreinte SHA-256, outil et version utilises.

# Gotchas

- **Ne pas figer la version d'Inno Setup.** Le script source de `mcp-search-net`
  exigeait exactement `6.7.1` et **rejetait** Inno Setup 7. Le driver de ce skill
  accepte 6 **et** 7. De plus, `ISCC.exe` expose une `ProductVersion` egale a
  `0.0.0.0` (le moteur affiche pourtant `7.0.2` dans sa banniere) : ne jamais
  gater la compilation sur cette propriete.
- **`/VERYSILENT` via `Start-Process`.** Passer les commutateurs Inno Setup dans
  un **tableau** `-ArgumentList`, pas dans une chaine unique — sous certains
  environnements une chaine `& $exe /VERYSILENT ...` est mal decoupee et l'appel
  echoue. Le tableau `@('/VERYSILENT',...)` fonctionne.
- **`jpackage` app-image est fenetre par defaut.** Une app console empaquetee
  sans `--win-console` se lance et sort proprement (exit 0) mais **n'affiche
  rien** : stdout est detache. Ajouter `--win-console` pour tout outil CLI.
- **`PrivilegesRequired=lowest` + `{localappdata}`** rendent l'installation
  silencieuse verifiable **sans droits admin**. Installer dans `Program Files`
  exigerait une elevation et casserait la verification headless.
- **AppId stable.** Le driver derive l'`AppId` Inno Setup d'un hash MD5 du nom de
  l'app : deux builds du meme nom partagent l'`AppId`, donc Windows les traite
  comme une mise a jour (et non deux programmes distincts).

# Troubleshooting

| Symptome | Cause | Correctif |
|----------|-------|-----------|
| `ISCC.exe introuvable` | Inno Setup absent | `winget install --id JRSoftware.InnoSetup` ou `-IsccPath` |
| `Jeton non resolu dans le modele Inno Setup : @@...@@` | Modele personnalise incomplet | ajouter la substitution correspondante dans le driver |
| `Le dossier payload est vide` | mauvais `-PayloadDir` | pointer vers le dossier de build reel |
| Le lanceur jpackage n'affiche rien | app-image fenetre | rebuild avec `--win-console` |
| `Remove-Item on ... '/VERYSILENT:' is blocked` | commutateurs passes en chaine | utiliser `-ArgumentList @('/VERYSILENT',...)` |

# Criteres de validation

- [ ] Le `.exe` existe et commence par le magic `MZ`
- [ ] Les metadonnees de version (ProductName/ProductVersion) sont correctes
- [ ] L'empreinte SHA-256 est calculee et enregistree (recette A)
- [ ] L'installation silencieuse renvoie le code 0 et depose le payload (recette A)
- [ ] Le lanceur natif s'execute et produit la sortie attendue (recette B)

# Exemples

Voir [`examples/example.md`](examples/example.md) pour l'execution complete de
bout en bout (generation + verification + installation silencieuse) avec les
sorties reelles observees.

# Limites

- Ne signe pas les executables (Authenticode) : SmartScreen restera actif.
- Ne gere pas la generation multi-architecture (x64 uniquement dans le modele).
- La recette B `app-image` produit un dossier avec lanceur ; pour un installateur
  Java complet (`--type exe`), WiX 3.x est requis en plus (non couvert ici).
- N'automatise pas la publication (GitHub Release, etc.) : voir les scripts
  `publish-*` du projet source pour ce volet.
