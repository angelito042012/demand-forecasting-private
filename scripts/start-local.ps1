# Inicia SOLO los procesos propios de la demostracion local: API (127.0.0.1:8000) y frontend (localhost:4200).
# No toca otros contenedores ni procesos. Los PID quedan en artifacts/private/t08/pids.json para stop-local.ps1.
# Requiere MongoDB en 127.0.0.1:27017 (contenedor df-mongo-dev ya existente; este script no lo crea ni lo detiene).
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$logs = Join-Path $root 'artifacts/private/t08'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$pidFile = Join-Path $logs 'pids.json'
if (Test-Path -LiteralPath $pidFile) { throw "Ya hay un registro de procesos ($pidFile). Ejecute scripts/stop-local.ps1 primero." }
$env:APP_ENV = 'development'
if (-not $env:COOKIE_SECURE) { $env:COOKIE_SECURE = 'false' }   # excepcion local explicita (HTTP); en despliegue HTTPS debe ser true
$py = Join-Path $root '.venv/Scripts/python.exe'
$api = Start-Process -FilePath $py -ArgumentList '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000', '--no-proxy-headers' `
    -WorkingDirectory $root -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'api.out.log') -RedirectStandardError (Join-Path $logs 'api.err.log')
$web = Start-Process -FilePath 'npm.cmd' -ArgumentList 'start', '--', '--host', '127.0.0.1', '--port', '4200' `
    -WorkingDirectory (Join-Path $root 'frontend') -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'web.out.log') -RedirectStandardError (Join-Path $logs 'web.err.log')
@{ api = $api.Id; web = $web.Id; started_utc = (Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding utf8
Write-Output "API: http://127.0.0.1:8000/api/v1/health (PID $($api.Id)); Web: http://localhost:4200 (PID $($web.Id)). Logs en $logs."
