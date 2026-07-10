param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$User = 'bober',
    [string]$ProjectDir = '/home/bober/projects/AI_Assistant',
    [switch]$StopPostgres
)

$ErrorActionPreference = 'Stop'

Write-Host '==> Stopping dev servers' -ForegroundColor Cyan
wsl -d $Distro -u $User bash -lc 'pkill -f [u]vicorn.*app.main:app 2>/dev/null || true; pkill -f [n]ode\ .*vite 2>/dev/null || true; pkill -f [v]ite\ --host 2>/dev/null || true'

if ($StopPostgres) {
    Write-Host '==> Stopping PostgreSQL' -ForegroundColor Cyan
    wsl -d $Distro -u $User bash -lc ('cd ' + $ProjectDir + ' && docker compose stop postgres')
}
