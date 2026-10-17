param([Parameter(Mandatory=$true)][string]$PythonExe)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$taskTemp = Join-Path $projectRoot '.setup-temp'
New-Item -ItemType Directory -Force -Path $taskTemp | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.pip-cache'
& $PythonExe -c 'import sys; assert sys.version_info[:2] == (3,12), "Usar Python 3.12"'
if ($LASTEXITCODE -ne 0) { throw 'Version Python no compatible con la base elegida.' }
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno.' }
}
& $venvPython -c 'import sys; assert sys.version_info[:2] == (3,12)'
if ($LASTEXITCODE -ne 0) { throw 'El entorno existente no es Python 3.12; revisar sin borrarlo.' }
& $venvPython -m pip --version 2>$null
if ($LASTEXITCODE -ne 0) {
    & $venvPython -m ensurepip --upgrade --default-pip
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo reparar pip en el entorno local.' }
}
$requirements = if (Test-Path requirements.lock.txt) { 'requirements.lock.txt' } else { 'requirements.in' }
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Instalacion incompleta.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias incompatibles.' }
$frozen = & $venvPython -m pip freeze
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron registrar versiones.' }
$frozen | Set-Content -Encoding utf8 requirements.lock.txt
Write-Output 'Dependencias instaladas y versiones registradas. Falta comprobar MongoDB y la aplicacion.'
