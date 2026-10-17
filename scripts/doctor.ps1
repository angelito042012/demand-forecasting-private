$ErrorActionPreference = 'Stop'
foreach ($name in @('claude','git','node','npm.cmd','docker')) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    if ($found) { Write-Output "$name : $($found.Source)" }
    else { Write-Output "$name : NO ENCONTRADO" }
}
if (Get-Command claude -ErrorAction SilentlyContinue) { & claude --version }
if (Get-Command git -ErrorAction SilentlyContinue) { & git --version }
if (Get-Command node -ErrorAction SilentlyContinue) { & node --version }
if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker info --format '{{.ServerVersion}}' 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Output 'Docker instalado; motor no accesible.' }
}
$projectRoot = Split-Path $PSScriptRoot -Parent
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython --version
    & $venvPython -m pip check
} else { Write-Output 'Entorno Python local pendiente.' }
