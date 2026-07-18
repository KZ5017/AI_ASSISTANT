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
- LM Studio native provider health/list/select/load/unload/chat endpointokkal, opcionális API authentication headerrel.
- Runtime chat modellvalasztas a UI-bol.
- Mentett beszelgetesek, uj chat, rename, soft delete.
- Streamelt uzenetkuldes, Markdown assistant valaszok, copy, csak legutolso assistant valasz streamelt ujrageneralasa.
- Stream kozben leallitas gomb; stop/hiba utan az utolso megvalaszolatlan user uzenet ujrakuldheto vagy inline szerkesztheto.
- Egysegesitett error/notice MVP: magyarabb hibak, composer warning helper, modellpanel success/warning/error notice-ok.
- Gondolkodo/reasoning kapcsolo `Lightbulb` / `LightbulbOff` ikonnal.
- Tudásbázis/Obsidian tool mode: LM Studio MCP integration request-szintu engedelyezese, Excel-prompt mintajara egyszerusitett magyar vault-only prompt policy, `00-INDEX.md` utvalaszto hasznalata, user prompt tiszta mentese.
- Adatbázis/Excel tool mode: LM Studio MCP integration request-szintu engedelyezese, letisztitott index-router read-only Excel prompt policy, celzott toolhasznalat, user prompt tiszta mentese; a prompt a tul eros munkafolyamat-tilto kor utan vissza lett egyszerusitve a stabilabb 9B-s viselkedes erdekeben.
- Reasoning delta UI: `Gondolkodik` allapot, lenyithato `Gondolatmenet`, preview/expanded mod, Markdown render, whitespace normalizalas es user-respectful manual scroll override.
- Mentett reasoning artifactok: a backend `reasoning_content` mezoben megorzi a streaming reasoninget, a frontend alapbol csukott `SavedReasoningPanel` disclosure-kent mutatja, de a provider/context builder es a 120000 karakteres guard nem szamolja bele.
- Explicit 120000 karakteres prompt/context vedelem frontend es backend oldalon.
- Light/dark tokenizalt UI.
- Legutobbi UI/performance polish zaras: composer/chatfolyam kozepszinkron, finomitott textarea shell, scrollbar kezeles, aljara ugras gomb, also fade, send gomb animacio, vegig lathato pending typing indicator, user buborek sortores/scrollbar finomitas, egységesített conversation rail sorritmus es hosszabb chatfolyam melletti MessageThread memoizacio.
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
    tool_modes.py
    routers/
      health.py
      assistant.py
      lm_studio.py
  alembic/
  tests/
frontend/
  src/
    api/assistant.ts
    hooks/useAutosizeTextarea.ts
    hooks/useModelState.ts
    hooks/useThreadScrollFollow.ts
    components/ChatShell.tsx
    components/ConversationRail.tsx
    components/MessageThread.tsx
    components/Composer.tsx
    components/ComposerModeBar.tsx
    components/ModelPanel.tsx
    components/ChatDialogs.tsx
    utils/notices.ts
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
AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian
AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID=mcp/excel
# Optional, required when LM Studio API authentication is enabled:
AI_ASSISTANT_LM_STUDIO_API_TOKEN=
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

Legutobbi ismert ellenorzes: `cd backend && .venv/bin/python -m pytest tests/test_tool_modes.py` 7 passed, `npm --prefix frontend run build` passed, `git diff --check` tiszta. Korabbi nagyobb zaras: `pytest -q` 40 passed. A normal send, regenerate streaming, megvalaszolatlan user uzenet recovery flow, reasoning delta UI, manual scroll override, saved reasoning artifact MVP, ChatShell hook-bontas, MessageThread render performance memoizacio, LM Studio API auth, szigoritott Obsidian/Tudásbázis tool mode, Excel/Adatbázis tool mode, Markdown layout hygiene es a legutobbi UI polish blokk rendben volt.

## Kovetkezo irany

A streaming, reasoning delta UI, manual scroll override, saved reasoning artifact MVP, ChatShell hook-bontas, Obsidian/Tudásbázis MVP szigoritott magyar vault-only prompttal, Excel/Adatbázis MVP, Excel index-router/toolhasznalat prompt finomitas, LM Studio `/v1/responses` + remote MCP kutatasi jegyzet, Markdown layout hygiene MVP es a composer/chatfolyam/rail UI polish blokk kesz. A mostani terv szerinti allapotot veglegesnek tekintjuk; tovabbi munka uj funkcio vagy konkret hasznalati visszajelzes alapjan induljon. Parkolopalyan marad: saved reasoning karakterhossz kijelzes, kulon reasoning copy gomb, stream status text es delta throttling.
