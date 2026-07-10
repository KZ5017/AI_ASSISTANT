param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$User = 'bober',
    [string]$ProjectDir = '/home/bober/projects/AI_Assistant',
    [switch]$SkipPostgres,
    [switch]$SkipMigration
)

$ErrorActionPreference = 'Stop'

function Invoke-WslStep {
    param([string]$Name, [string]$Command)
    Write-Host ('==> ' + $Name) -ForegroundColor Cyan
    wsl -d $Distro -u $User bash -lc $Command
}

if (-not $SkipPostgres) {
    Invoke-WslStep 'Starting PostgreSQL' ('cd ' + $ProjectDir + ' && docker compose up -d postgres')
}

if (-not $SkipMigration) {
    Invoke-WslStep 'Running Alembic migrations' ('cd ' + $ProjectDir + '/backend && source .venv/bin/activate && alembic upgrade head')
}

Invoke-WslStep 'Stopping old dev servers' 'pkill -f [u]vicorn\ app.main:app 2>/dev/null || true; pkill -f [v]ite.*5173 2>/dev/null || true'
Invoke-WslStep 'Starting backend on 0.0.0.0:8000' ('cd ' + $ProjectDir + '/backend && setsid -f bash -lc ' + [char]39 + 'source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null' + [char]39)
Invoke-WslStep 'Starting frontend on 0.0.0.0:5173' ('cd ' + $ProjectDir + '/frontend && setsid -f bash -lc ' + [char]39 + 'npm run dev -- --host 0.0.0.0 > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null' + [char]39)
Start-Sleep -Seconds 2
Invoke-WslStep 'Listener status' 'ss -ltnp | grep :8000 || true; ss -ltnp | grep :5173 || true'

Write-Host ''
Write-Host 'App:          http://localhost:5173' -ForegroundColor Green
Write-Host 'API docs:     http://localhost:8000/docs' -ForegroundColor Green
Write-Host ('Backend log:  wsl -d ' + $Distro + ' -u ' + $User + ' tail -f /tmp/ai-assistant-backend.log')
Write-Host ('Frontend log: wsl -d ' + $Distro + ' -u ' + $User + ' tail -f /tmp/ai-assistant-frontend.log')
