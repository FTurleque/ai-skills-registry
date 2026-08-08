# Exemple — Generation d'un installateur `.exe` de bout en bout

Execution reelle sous Windows 10 / PowerShell 7 / Inno Setup 7.0.2 / JDK 24.0.1.
Toutes les sorties ci-dessous ont ete observees pendant la creation du skill.

---

## Recette A — Installateur Inno Setup

### 1. Payload minimal

```bash
mkdir -p payload/bin
printf '@echo off\r\necho Hello from demo-app!\r\n' > payload/bin/demo-app.cmd
printf 'demo-app 1.0.0\r\n' > payload/README.txt
```

### 2. Generation du `.exe`

```powershell
./resources/build-exe.ps1 `
  -PayloadDir ./payload `
  -AppName demo-app `
  -Version 1.0.0 `
  -AppPublisher "Fabrice Turleque" `
  -OutputDir ./dist
```

Sortie :

```
Compiler engine version: Inno Setup 7.0.2
   Compressing: ...\payload\README.txt
   Compressing: ...\payload\bin\demo-app.cmd
Successful compile. Resulting Setup program filename is:
...\dist\demo-app-1.0.0-windows-x64-setup.exe

EXE GENERE AVEC SUCCES
Setup    : ...\dist\demo-app-1.0.0-windows-x64-setup.exe
SHA-256  : f1eed147bba323fed027dba8743073368edc60b152d6622cd1d070e78df0add8
AppId    : {{C558494D-C533-87EE-E1D5-8B802F00E837}
Inno     : ...\Inno Setup 7\ISCC.exe
```

### 3. Verification du PE

```powershell
$exe = "./dist/demo-app-1.0.0-windows-x64-setup.exe"
$bytes = [System.IO.File]::ReadAllBytes($exe)
$magic = -join ($bytes[0..1] | ForEach-Object { [char]$_ })
"$magic  $((Get-Item $exe).VersionInfo.ProductName) $((Get-Item $exe).VersionInfo.ProductVersion)"
```

Sortie :

```
Taille   : 2 088 775 octets
PE magic : MZ  (MZ = executable Windows valide)
Produit  : demo-app  1.0.0
```

### 4. Installation silencieuse (sans admin) + execution

```powershell
$exe = "./dist/demo-app-1.0.0-windows-x64-setup.exe"
$target = "./installed"
$args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$target","/LOG=install.log")
$p = Start-Process -FilePath $exe -ArgumentList $args -Wait -PassThru
"Exit code : $($p.ExitCode)"
Get-ChildItem -Recurse $target | Select-Object -ExpandProperty FullName
& "$target/bin/demo-app.cmd"
```

Sortie :

```
Exit code : 0
...\installed\bin
...\installed\README.txt
...\installed\unins000.dat
...\installed\unins000.exe
...\installed\bin\demo-app.cmd
Hello from demo-app!
```

L'installateur a depose le payload **et** genere un desinstalleur `unins000.exe`,
et le binaire installe s'execute correctement.

---

## Recette B — Lanceur natif jpackage (Java)

### 1. JAR executable minimal

```powershell
# Main.java : System.out.println("Hello from demo-java jpackage exe!");
javac -d classes Main.java
jar --create --file input/app.jar --main-class Main -C classes .
```

### 2. Generation du lanceur `.exe`

```powershell
jpackage --type app-image --name demo-java-cli `
  --input ./input --main-jar app.jar --main-class Main `
  --win-console `
  --dest ./out
& "./out/demo-java-cli/demo-java-cli.exe"
```

Sortie :

```
exit jpackage: 0
Sortie ->
Hello from demo-java jpackage exe!
```

> **Gotcha verifie** : sans `--win-console`, le meme lanceur se termine avec le
> code 0 mais n'affiche **rien** (application fenetree, stdout detache).
