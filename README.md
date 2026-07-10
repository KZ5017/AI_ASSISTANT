# AI Assistant Standalone

Ez a konyvtar mar egy mukodo standalone, lokalis AI chat webapp scaffold es implementacio alapja. Nem a BoberDetective projekt resze, nem hasznal BoberDetective domain funkciokat, es nem epit BoberDetective adatbazisra.

Cel: altalanos, lokalis LM Studio chat alkalmazas mentett beszelgetesekkel, modellallapot-kezelovel es letisztult light/dark UI-val.

## Jelenlegi allapot

Megvalosult:

- FastAPI backend `/api` prefix alatt.
- PostgreSQL + SQLAlchemy + Alembic persistence.
- Kulon standalone Postgres kontener es volume: `ai-assistant-postgres`, `ai_assistant_postgres_data`.
- Host Postgres port: `55432`, hogy ne utkozzon a BoberDetective `5432` portjaval.
- React + Vite + TypeScript frontend.
- LM Studio native provider health/list/select/load/unload/chat endpointokkal.
- Runtime chat modellvalasztas a UI-bol.
- Mentett beszelgetesek, uj chat, rename, soft delete.
- Uzenetkuldes, Markdown assistant valaszok, copy, csak legutolso assistant valasz ujrageneralasa.
- Gondolkodo/reasoning kapcsolo `Lightbulb` / `LightbulbOff` ikonnal.
- Explicit 120000 karakteres prompt/context vedelem frontend es backend oldalon.
- Light/dark tokenizalt UI.
- Windows/PowerShell indito, statusz es leallito scriptek.

Nem cel es nincs benne:

- case, document, OCR, Docling,
- RAG, Qdrant, embedding index,
- source reference,
- nyomozati objektumok,
- audit/provenance workflow,
- BoberDetective brand vagy adatbazis.

## Strukturak

```text
backend/
  app/
    main.py
    config.py
    db.py
    models.py
    schemas.py
    assistant_service.py
    llm_provider.py
    model_runtime.py
    routers/
      health.py
      assistant.py
      lm_studio.py
  alembic/
  tests/
frontend/
  src/
    api/assistant.ts
    components/ChatShell.tsx
    styles/tokens.css
    styles/app.css
scripts/
  start.ps1
  status.ps1
  stop.ps1
```

## Inditas Windows PowerShellbol - STABIL, ELFOGADOTT MOD

Ezt hasznald. Ez a BoberDetective-nel bevalt WSL/PowerShell minta standalone valtozata, es Windowsbol tesztelve mukodik.

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

A `scripts/start.ps1` szandekosan egyszeru:

1. elinditja a standalone Postgres es lefuttatja az Alembic migraciot,
2. var 5 masodpercet,
3. kozvetlen `setsid -f` paranccsal inditja a backendet,
4. var 5 masodpercet,
5. kozvetlen `setsid -f` paranccsal inditja a frontendet.

Fontos: a start scriptben nincs portproxy, nincs admin jog igeny, nincs belso `sh -c`, es nincs `pkill`. A leallitas a `scripts/stop.ps1` feladata. Ezt ne bonyolitsuk ujra, mert a mukodo megoldas pont az egyszerusege miatt stabil.

URL-ek Windowsbol:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/health

Reszletek: `WINDOWS_START.md`.

## Kezi backend inditas WSL-ben

```bash
cd /home/bober/projects/AI_Assistant
docker compose up -d postgres
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Kezi frontend inditas WSL-ben

```bash
cd /home/bober/projects/AI_Assistant/frontend
npm install
npm run dev -- --host 0.0.0.0
```

## Fontos env defaultok

Backend `.env.example`:

```bash
AI_ASSISTANT_DATABASE_URL=postgresql+psycopg://ai_assistant:ai_assistant@localhost:55432/ai_assistant
AI_ASSISTANT_LM_STUDIO_BASE_URL=http://127.0.0.1:1234
AI_ASSISTANT_LM_STUDIO_CHAT_MODEL=qwen/qwen3.6-35b-a3b
AI_ASSISTANT_CONTEXT_CHAR_BUDGET=120000
```

Frontend `.env.example`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## Ellenorzes

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
ruff check app tests
```

Frontend:

```bash
cd frontend
npm run build
```

Legutobbi ismert frontend build: sikeres.
