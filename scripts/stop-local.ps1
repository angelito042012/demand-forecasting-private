# Detiene unicamente los procesos registrados por start-local.ps1 (y sus hijos). No toca MongoDB ni otros contenedores.
# Un PID solo se detiene si la hora de inicio y el ejecutable coinciden con lo registrado: si el sistema reutilizo el
# PID para otro programa, NO se detiene y se informa.
param([string]$RegistryPath = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$registry = if ($RegistryPath) { $RegistryPath } else { Join-Path $root 'artifacts/private/t08/procesos.json' }
if (-not (Test-Path -LiteralPath $registry)) { Write-Output 'No hay procesos registrados.'; exit 0 }
$reg = Get-Content -LiteralPath $registry -Raw | ConvertFrom-Json
foreach ($e in @($reg.procesos)) {
    $p = Get-Process -Id $e.pid -ErrorAction SilentlyContinue
    if ($null -eq $p) { Write-Output "$($e.name): ya no estaba en ejecucion."; continue }
    $sameStart = [math]::Abs(($p.StartTime.ToUniversalTime() - [datetime]::Parse($e.start).ToUniversalTime()).TotalSeconds) -lt 2
    $sameExe = $p.Path -eq $e.exe
    if ($sameStart -and $sameExe) {
        try { & cmd.exe /c "taskkill /PID $($e.pid) /T /F >nul 2>&1" } catch { }
        Write-Output "$($e.name): detenido (PID $($e.pid))."
    } else {
        Write-Output "$($e.name): el PID $($e.pid) pertenece ahora a otro proceso (hora de inicio o ejecutable distintos); NO se detiene."
    }
}
Remove-Item -LiteralPath $registry -Force
Write-Output 'Procesos propios detenidos.'
