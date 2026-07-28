# Windows / PowerShell inditas

Az AI Assistant onallo lokal AI chat alkalmazas. A BoberDetective-et nem kezeli, es a ket alkalmazas parhuzamosan futhat:

- AI Assistant frontend/backend: `5173` / `8000`
- AI Assistant PostgreSQL: `127.0.0.1:56000`
- BoberDetective frontend/backend: `5174` / `8001`

A `55432-55731` Windows rendszeraltal kizart porttartomany, ezert adatbazishoz ne valassz innen portot.

## Inditas

Barmelyik Windows mappabol:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

A script elinditja a sajat PostgreSQL kontenert, megvarja annak keszenleti allapotat, migral, levlasztva elinditja a backendet es frontendet, majd health ellenorzessel visszaadja a PowerShell promptot.

## Allapot

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\status.ps1
```

## Leallitas

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\stop.ps1
```

A leallitas csak az AI Assistant sajat backend/frontend folyamatait es Compose-keszletet allitja le. A Postgres volume megmarad, BoberDetective-hez nem nyul.

## URL-ek

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/health

## Logok

```powershell
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-backend.log
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-frontend.log
```

## Kezi inditas

Hibaelharitashoz a backendet a sajat munkakonyvtarabol inditsd, kulonben nem tolti be a `backend/.env` adatbazis- es LM Studio-beallitasait:

```bash
cd /home/bober/projects/AI_Assistant

docker compose up -d postgres
cd backend
.venv/bin/alembic upgrade head
setsid -f sh -c 'echo $$ > /tmp/ai-assistant-backend.pid; exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/ai-assistant-backend.log 2>&1 < /dev/null' >/dev/null 2>&1 < /dev/null

cd /home/bober/projects/AI_Assistant
setsid -f sh -c 'echo $$ > /tmp/ai-assistant-frontend.pid; exec npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173 --strictPort > /tmp/ai-assistant-frontend.log 2>&1 < /dev/null' >/dev/null 2>&1 < /dev/null
```