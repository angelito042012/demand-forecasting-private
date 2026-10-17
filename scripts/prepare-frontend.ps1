$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (Test-Path -LiteralPath 'frontend') { throw 'frontend ya existe; revisar su contenido antes de continuar.' }
$env:npm_config_cache = Join-Path $projectRoot '.npm-cache'
$env:NG_CLI_ANALYTICS = 'false'
& npx.cmd --yes --package '@angular/cli@21' ng new frontend --directory frontend --routing --style scss --standalone --skip-git --package-manager npm --defaults
if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar Angular. Revisar conectividad con registry.npmjs.org y carpeta parcial.' }
Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Angular generado pero compilacion fallida.' }
Write-Output 'Base Angular generada y compilada. Conservar package-lock.json.'
