# Inicia SOLO los procesos propios de la demostracion local: API (127.0.0.1:8000), frontend (localhost:4200) y UN worker.
# Opcional: -Scheduler -EnableScheduler inicia el temporizador local (deshabilitado por defecto; ver docs/GUIA_LOCAL.md).
# Registra por proceso {nombre, pid, hora de inicio, ejecutable} en artifacts/private/t08/procesos.json para que
# stop-local.ps1 solo detenga un PID cuando la hora de inicio y el ejecutable coinciden (nunca por un PID reutilizado).
# Requiere MongoDB en 127.0.0.1:27017 (contenedor df-mongo-dev ya existente; este script no lo crea ni lo detiene).
param([switch]$Scheduler, [switch]$EnableScheduler, [int]$SchedulerMinutes = 1440)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$logs = Join-Path $root 'artifacts/private/t08'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$registry = Join-Path $logs 'procesos.json'
if (Test-Path -LiteralPath $registry) { throw "Ya hay un registro de procesos ($registry). Ejecute scripts/stop-local.ps1 primero." }
$env:APP_ENV = 'development'
if (-not $env:COOKIE_SECURE) { $env:COOKIE_SECURE = 'false' }   # excepcion local explicita (HTTP); en despliegue HTTPS debe ser true
$py = Join-Path $root '.venv/Scripts/python.exe'
$entries = @()

function Start-Tracked([string]$name, [string]$file, [string[]]$arguments, [string]$workdir) {
    $p = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $workdir -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "$name.out.log") -RedirectStandardError (Join-Path $logs "$name.err.log")
    Start-Sleep -Milliseconds 400
    $p.Refresh()
    return [pscustomobject]@{ name = $name; pid = $p.Id; start = $p.StartTime.ToUniversalTime().ToString('o'); exe = $p.Path }
}

$entries += Start-Tracked 'api' $py @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000', '--no-proxy-headers') $root
$entries += Start-Tracked 'web' 'npm.cmd' @('start', '--', '--host', '127.0.0.1', '--port', '4200') (Join-Path $root 'frontend')
$entries += Start-Tracked 'worker' $py @('-m', 'pipeline.jobs.worker', '--poll-seconds', '3', '--worker-id', 'local-1') $root
if ($Scheduler) {
    if (-not $EnableScheduler) { throw 'El temporizador esta deshabilitado por defecto: use -Scheduler -EnableScheduler para activarlo de forma explicita.' }
    $entries += Start-Tracked 'scheduler' $py @('-m', 'pipeline.jobs.scheduler', '--loop', '--enable', '--interval-minutes', "$SchedulerMinutes") $root
}
@{ iniciado_utc = (Get-Date).ToUniversalTime().ToString('o'); procesos = $entries } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $registry -Encoding utf8
Write-Output "API http://127.0.0.1:8000/api/v1/health | Web http://localhost:4200 | worker local-1$(if ($Scheduler) { ' | temporizador cada ' + $SchedulerMinutes + ' min' }). Procesos registrados en $registry; logs en $logs."
