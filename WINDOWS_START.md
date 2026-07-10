# Windows / PowerShell inditas - stabil elfogadott mod

Ez a dokumentum a mukodo, letesztelt inditasi modot rogziti. Ne terjunk vissza portproxyhoz vagy bonyolult wrapperhez, amig nincs ra konkret, reprodukalhato ok.

## URL-ek Windowsbol

- App: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/health

A frontend Vite dev server `0.0.0.0:5173` cimen hallgat WSL-ben, es `/api` proxyval tovabbit a backendnek.
A backend `0.0.0.0:8000` cimen indul.
A standalone PostgreSQL host portja `55432`, hogy ne utkozzon mas lokalis Postgres peldanyokkal.

## Egyetlen ajanlott inditas PowerShellbol

Barmelyik Windows mappabol futtathato:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

A script jelenlegi, elfogadott logikaja:

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant && docker compose up -d postgres && cd backend && source .venv/bin/activate && alembic upgrade head'
Start-Sleep -Seconds 5
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/backend && setsid -f .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null'
Start-Sleep -Seconds 5
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/frontend && setsid -f npm run dev -- --host 0.0.0.0 > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null'
```

## Fontos tanulsagok, ne kovessuk el ujra

- Ne legyen `pkill` a start scriptben ugyanabban a parancsban, ahol kesobb `uvicorn` vagy `vite` szerepel. A `pkill -f` kepes a sajat indito parancssorat is eltalalni.
- Ne hasznaljunk belso `sh -c "..."` reteget a PowerShell -> WSL -> bash lancban. Az idezojelezes konnyen szetesik, es peldaul `npm run dev` helyett csak az `npm` help fut le.
- Ne kelljen admin jog vagy `netsh portproxy`. A mukodo megoldas sima WSL `setsid -f` inditas.
- A stop script feleljen a regi folyamatok leallitasert, a start script csak inditson.
- A ket 5 masodperces varakozas szandekos, gyakorlati stabilizalo lepes.

## Leallitas

Fejlesztoi szerverek leallitasa:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\stop.ps1
```

Fejlesztoi szerverek es standalone Postgres leallitasa:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\stop.ps1 -StopPostgres
```

## Ellenorzes

WSL listener ellenorzes:

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'ss -ltnp | grep -E ":(8000|5173)"'
```

Logok:

```powershell
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-backend.log
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-frontend.log
```

## Kezi parancslista script nelkul

Ha valaha a script helyett kezzel kell inditani, ezt a harom parancsot hasznald ebben a sorrendben:

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant && docker compose up -d postgres && cd backend && source .venv/bin/activate && alembic upgrade head'
```

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/backend && setsid -f .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null'
```

```powershell
wsl -d Ubuntu-24.04 -u bober bash -lc 'cd /home/bober/projects/AI_Assistant/frontend && setsid -f npm run dev -- --host 0.0.0.0 > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null'
```
