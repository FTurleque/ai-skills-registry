<#
.SYNOPSIS
    Genere un installateur Windows (.exe) a partir d'un dossier payload, via Inno Setup.

.DESCRIPTION
    Driver distille depuis le pipeline de release de mcp-search-net
    (scripts/release/build-windows-installer.ps1). Il :
      1. localise ISCC.exe (compilateur Inno Setup) sur la machine ;
      2. genere un script .iss depuis installer.iss.template (substitution de jetons) ;
      3. compile l'installateur en .exe ;
      4. calcule l'empreinte SHA-256 du .exe produit.

    Contrairement au script source, ce driver n'impose PAS une version exacte
    d'Inno Setup : il accepte Inno Setup 6 comme 7 (voir Gotchas dans SKILL.md).

.EXAMPLE
    ./build-exe.ps1 -PayloadDir ./payload -AppName demo-app -Version 1.0.0

.NOTES
    Doit tourner sur Windows (ISCC.exe est un binaire Windows).
#>
[CmdletBinding()]
param(
    # Dossier dont tout le contenu sera empaquete dans l'installateur.
    [Parameter(Mandatory)]
    [string] $PayloadDir,

    # Nom court de l'application (kebab-case conseille).
    [Parameter(Mandatory)]
    [string] $AppName,

    # Version SemVer (ex. 1.0.0, 1.2.3-rc1).
    [Parameter(Mandatory)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$')]
    [string] $Version,

    [string] $AppPublisher = 'Unknown Publisher',

    # Modele .iss ; par defaut celui livre a cote du driver.
    [string] $Template = (Join-Path $PSScriptRoot 'installer.iss.template'),

    # Dossier de sortie du .exe.
    [string] $OutputDir = (Join-Path (Get-Location).Path 'dist'),

    # Chemin explicite vers ISCC.exe (sinon auto-detection).
    [string] $IsccPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($env:OS -ne 'Windows_NT') {
    throw "Inno Setup ne fonctionne que sur Windows : ISCC.exe est un binaire Windows."
}

$PayloadDir = [System.IO.Path]::GetFullPath($PayloadDir)
if (-not (Test-Path -LiteralPath $PayloadDir -PathType Container)) {
    throw "Dossier payload introuvable : $PayloadDir"
}
if (-not (Test-Path -LiteralPath $Template -PathType Leaf)) {
    throw "Modele Inno Setup introuvable : $Template"
}
if (@(Get-ChildItem -LiteralPath $PayloadDir -Force).Count -eq 0) {
    throw "Le dossier payload est vide : $PayloadDir"
}

# --- 1. Localiser ISCC.exe -------------------------------------------------
function Find-Iscc {
    param([string] $Explicit)
    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        if (Test-Path -LiteralPath $Explicit -PathType Leaf) { return $Explicit }
        throw "ISCC.exe introuvable au chemin fourni : $Explicit"
    }
    $candidates = @()
    $onPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($onPath) { $candidates += $onPath.Source }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe')
        $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
    }
    foreach ($pf in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if (-not [string]::IsNullOrWhiteSpace($pf)) {
            $candidates += (Join-Path $pf 'Inno Setup 7\ISCC.exe')
            $candidates += (Join-Path $pf 'Inno Setup 6\ISCC.exe')
        }
    }
    $candidates += 'C:\ProgramData\chocolatey\bin\ISCC.exe'
    $found = $candidates |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_ -PathType Leaf) } |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($found)) {
        throw @"
ISCC.exe (compilateur Inno Setup) introuvable.
Installez Inno Setup :  winget install --id JRSoftware.InnoSetup
ou passez -IsccPath 'C:\chemin\vers\ISCC.exe'.
"@
    }
    return $found
}

$Iscc = Find-Iscc -Explicit $IsccPath
$IsccVersion = (Get-Item -LiteralPath $Iscc).VersionInfo.ProductVersion

# --- 2. Preparer les valeurs ----------------------------------------------
# AppId Inno Setup : GUID stable derive deterministiquement du nom de l'app,
# pour que les mises a jour se reconnaissent entre elles (meme AppId => upgrade).
$md5 = [System.Security.Cryptography.MD5]::Create()
$hash = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("ai-skills-registry:$AppName"))
$AppId = '{{' + ([System.Guid]::new($hash)).ToString().ToUpperInvariant() + '}'

$BaseVersion = ($Version -split '[-+]')[0]
$NumericVersion = "$BaseVersion.0"
$OutputBaseName = "$AppName-$Version-windows-x64-setup"

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$WorkDir = Join-Path $OutputDir '.work'
New-Item -ItemType Directory -Force -Path $OutputDir, $WorkDir | Out-Null

$Setup = Join-Path $OutputDir "$OutputBaseName.exe"
$Checksum = "$Setup.sha256"
Remove-Item -LiteralPath $Setup, $Checksum -Force -ErrorAction SilentlyContinue

# --- 3. Generer le .iss depuis le modele ----------------------------------
function Escape-Inno([string] $v) { return $v.Replace('"', '""') }

$Utf8 = New-Object System.Text.UTF8Encoding($false)
$Iss = [System.IO.File]::ReadAllText($Template, $Utf8)
$Iss = $Iss.Replace('@@APP_NAME@@',            (Escape-Inno $AppName))
$Iss = $Iss.Replace('@@VERSION@@',             (Escape-Inno $Version))
$Iss = $Iss.Replace('@@APP_NUMERIC_VERSION@@', (Escape-Inno $NumericVersion))
$Iss = $Iss.Replace('@@APP_ID@@',              (Escape-Inno $AppId))
$Iss = $Iss.Replace('@@APP_PUBLISHER@@',       (Escape-Inno $AppPublisher))
$Iss = $Iss.Replace('@@SOURCE_DIR@@',          (Escape-Inno $PayloadDir))
$Iss = $Iss.Replace('@@OUTPUT_DIR@@',          (Escape-Inno $OutputDir))
$Iss = $Iss.Replace('@@OUTPUT_BASENAME@@',     (Escape-Inno $OutputBaseName))

# Garde-fou : aucun jeton ne doit subsister, sinon Inno Setup echouerait mal.
if ($Iss -match '@@[A-Z0-9_]+@@') {
    throw "Jeton non resolu dans le modele Inno Setup : $($Matches[0])"
}

$GeneratedIss = Join-Path $WorkDir "$OutputBaseName.iss"
[System.IO.File]::WriteAllText($GeneratedIss, $Iss, $Utf8)

# --- 4. Compiler ----------------------------------------------------------
try {
    & $Iscc $GeneratedIss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup (ISCC) a echoue (code $LASTEXITCODE)" }
    if (-not (Test-Path -LiteralPath $Setup -PathType Leaf)) {
        throw "Executable setup non produit : $Setup"
    }

    $Hash = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $([System.IO.Path]::GetFileName($Setup))" | Set-Content -LiteralPath $Checksum -Encoding ascii

    Write-Host ''
    Write-Host "EXE GENERE AVEC SUCCES" -ForegroundColor Green
    Write-Host "Setup    : $Setup"
    Write-Host "SHA-256  : $Hash"
    Write-Host "AppId    : $AppId"
    Write-Host "Inno     : $Iscc"
    Write-Host "Inno Ver : $IsccVersion"
}
finally {
    Remove-Item -LiteralPath $GeneratedIss -Force -ErrorAction SilentlyContinue
}
