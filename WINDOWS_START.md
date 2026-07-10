# Windows / PowerShell inditas

Az app WSL2 Ubuntu alatt fut, de Windows oldalrol bongeszobol erheto el.

## URL-ek Windowsbol

- App: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/health

A frontend Vite dev server `0.0.0.0:5173` cimen hallgat WSL-ben, es `/api` proxyval tovabbit a backendnek.
A backend `0.0.0.0:8000` cimen indul.
A standalone PostgreSQL host portja `55432`, hogy ne utkozzon a BoberDetective `5432`-es Postgres portjaval.

Ha a Windows localhost forwarding nem mukodik, kerdezd le a WSL IP-t:

```powershell
wsl -d Ubuntu-24.04 -u bober hostname -I
```

Ezutan probald: `http://WSL-IP:5173`.

## Elso inditas PowerShellbol

```powershell
cd \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant
```

Ha az execution policy tiltja a helyi script futtatast:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Normal inditas:

```powershell
.\scripts\start.ps1
```

Ez elvegzi:

1. `docker compose up -d postgres`,
2. `alembic upgrade head`,
3. backend inditas `0.0.0.0:8000`,
4. frontend inditas `0.0.0.0:5173`.

Opcio:

```powershell
.\scripts\start.ps1 -SkipPostgres
.\scripts\start.ps1 -SkipMigration
```

## Statusz

```powershell
.\scripts\status.ps1
```

## Leallitas

```powershell
.\scripts\stop.ps1
.\scripts\stop.ps1 -StopPostgres
```

## Direkt futtatas barmelyik Windows mappabol

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

## Logok

```powershell
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-backend.log
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-frontend.log
```

## Kezi parancslista PowerShellbol script nelkul

Elso terminal:

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant && docker compose up -d postgres'
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/backend && source .venv/bin/activate && alembic upgrade head'
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000'
```

Masodik terminal:

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/frontend && npm run dev -- --host 0.0.0.0'
```
