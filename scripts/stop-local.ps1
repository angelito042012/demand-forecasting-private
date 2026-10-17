# Detiene unicamente los procesos registrados por start-local.ps1 (y sus hijos). No toca MongoDB ni otros contenedores.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pidFile = Join-Path $root 'artifacts/private/t08/pids.json'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output 'No hay procesos registrados.'; exit 0 }
$p = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($id in @($p.api, $p.web)) {
    if ($id) { try { & cmd.exe /c "taskkill /PID $id /T /F >nul 2>&1" } catch { } }  # un PID ya terminado no es un error
}
Remove-Item -LiteralPath $pidFile -Force
Write-Output 'Procesos propios detenidos.'
