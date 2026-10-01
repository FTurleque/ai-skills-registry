# Installation du superviseur de code (Windows).
#   .\install.ps1              installation globale (~/.claude)
#   .\install.ps1 -Uninstall   desinstallation
param([switch]$Uninstall, [string]$Project)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$python = $null
foreach ($candidate in @("python", "python3", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $python = $candidate; break }
}
if (-not $python) {
    Write-Error "Python 3 est introuvable dans le PATH. Installe Python 3.8 ou plus, puis relance."
    exit 1
}

$args = @()
if ($Uninstall) { $args += "--uninstall" }
if ($Project)   { $args += @("--project", $Project) }

& $python (Join-Path $here "install.py") @args
exit $LASTEXITCODE
