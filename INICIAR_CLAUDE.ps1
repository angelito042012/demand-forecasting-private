$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw 'Claude Code no esta disponible en esta terminal.'
}
$brief = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'RETOMAR_CLAUDE.md') -Raw -Encoding utf8
& claude $brief
