param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$User = 'bober',
    [switch]$StopPostgres
)

$ErrorActionPreference = 'Stop'
Write-Host '==> Stopping backend/frontend dev servers' -ForegroundColor Cyan
wsl -d $Distro -u $User bash -lc 'pkill -f [u]vicorn\ app.main:app 2>/dev/null || true; pkill -f [v]ite.*5173 2>/dev/null || true'
if ($StopPostgres) {
    Write-Host '==> Stopping PostgreSQL' -ForegroundColor Cyan
    wsl -d $Distro -u $User bash -lc 'cd /home/bober/projects/AI_Assistant && docker compose stop postgres'
}
