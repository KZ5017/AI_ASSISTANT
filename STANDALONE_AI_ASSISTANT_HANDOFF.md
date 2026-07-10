# Standalone AI Assistant Handoff

## Cel

A projekt egy teljesen fuggetlen, altalanos, lokalis AI chat webapp LM Studiohoz.

Nem BoberDetective modul kiszerelese, nem BoberDetective aloldal, es nem hasznal BoberDetective adatbazist. A referencia projektbol csak a kiprobalt backend/frontend mintak es UX dontesek voltak hasznalva.

## Hard boundary

A standalone appban tovabbra sem lehet:

- case,
- document,
- OCR,
- Docling,
- Qdrant,
- embedding/RAG,
- source reference,
- nyomozati objektum,
- audit/provenance workflow,
- BoberDetective brand.

Ha a user dokumentum-szoveget masol be, az sima chat input.

## Aktualis technikai allapot

Backend:

- FastAPI.
- SQLAlchemy + Alembic.
- PostgreSQL.
- httpx LM Studio native provider.
- pytest/ruff dev stack.

Frontend:

- React + Vite + TypeScript.
- lucide-react.
- react-markdown + remark-gfm.
- Tokenizalt light/dark CSS.

Infrastructure:

- WSL2 Ubuntu alatt fut a backend/frontend.
- Windows hoston fut az LM Studio.
- Backend LM Studio base URL default: `http://127.0.0.1:1234`.
- Standalone Postgres host port: `55432`.
- Windows start/status/stop scriptek vannak.

## Fobb fajlok

Backend:

- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/assistant_service.py`
- `backend/app/llm_provider.py`
- `backend/app/model_runtime.py`
- `backend/app/routers/assistant.py`
- `backend/app/routers/lm_studio.py`
- `backend/app/routers/health.py`

Frontend:

- `frontend/src/api/assistant.ts`
- `frontend/src/components/ChatShell.tsx`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/app.css`

Docs/state:

- `README.md`
- `IMPLEMENTATION_PLAN.md`
- `SCAFFOLD.md`
- `SMOKE_TEST.md`
- `WINDOWS_START.md`

## Backend API

Health:

- `GET /api/health`

Assistant:

- `GET /api/assistant/status`
- `GET /api/assistant/chats`
- `POST /api/assistant/chats`
- `GET /api/assistant/chats/{chat_id}`
- `PATCH /api/assistant/chats/{chat_id}`
- `DELETE /api/assistant/chats/{chat_id}`
- `POST /api/assistant/chats/{chat_id}/messages`
- `POST /api/assistant/chats/{chat_id}/regenerate`

LM Studio:

- `GET /api/lm-studio/health`
- `GET /api/lm-studio/models`
- `POST /api/lm-studio/select-chat-model`
- `POST /api/lm-studio/load-chat-model`
- `POST /api/lm-studio/unload-chat-model`
- `POST /api/lm-studio/chat`

## Chat persistence

Assistant chat:

- default title,
- status `active` / soft deleted state,
- reasoning mode,
- temperature,
- metadata,
- timestamps.

Assistant message:

- role `user` / `assistant` / `system`,
- content,
- sequence index,
- reasoning mode,
- model,
- token/meta fields,
- timestamps.

Soft delete mukodik: a chat nem jelenik meg az aktiv listaban, de az adatok nem torlodnek fizikailag.

## Kontextusvedelem

- Explicit budget: `120000` karakter.
- Frontend is elovalidal.
- Backend authoritative.
- Nincs csendes truncation.
- Tul hosszu prompt/context eseten kuldes tiltva es warning jelenik meg.

A composer warning jelenlegi UX-e:

- a beviteli mezo alatt van,
- allandoan fenntartott egysoros slotot hasznal,
- ures allapotban lathatatlan,
- megjeleneskor nem ugratja a layoutot.

Prioritas:

1. single prompt limit,
2. full context limit,
3. nincs betoltott chat modell.

## Reasoning / Gondolkodo

Frontend:

- alapertelmezett: kikapcsolva,
- kikapcsolva: `normal`, provider fele `off`,
- bekapcsolva: `model_default`, provider fele `model_default`,
- ikon: `LightbulbOff` kikapcsolva, `Lightbulb` bekapcsolva.

UI stilus:

- a Gondolkodo gomb a send-button primary csaladba tartozik,
- inaktiv allapotban halvany primary,
- aktiv allapotban teljes primary,
- szovegszin ugyanaz, mint a send ikon szine: `--color-on-primary`.

## LM Studio provider

Default chat model:

```bash
qwen/qwen3.6-35b-a3b
```

Load config defaultok `.env.example` szerint:

- context length: `61440`,
- eval batch size: `512`,
- flash attention: `true`,
- offload KV cache to GPU: `true`,
- auto-load chat model: `true`,
- default temperature: `0.1`,
- max output tokens: uresen hagyva omitted.

Provider viselkedes:

- `/api/v1/models` listazas model key-kel es loaded instance id-kkel,
- `/api/v1/models/load` arbitrary selected chat modelre,
- `/api/v1/models/unload` instance id vagy model id alapjan,
- `/api/v1/chat` chat completion,
- selected chat model runtime allapotban tarolva.

## Frontend UI jelenlegi allapot

Layout:

- bal oldali conversation rail,
- jobb oldali chat canvas,
- felso model/status panel,
- belso message-thread scroll,
- also composer.

Conversation rail:

- uj chat primary gomb,
- refresh icon button,
- mentett chat lista kulon szekciokent, felso borderrel elvalasztva,
- chat sorok alapbol csendesek,
- hoverre secondary gombtest,
- aktiv chat primary narancs,
- harompontos menu: Atnevezes, Torles.

Model panel:

- bal oldalon status, base URL, aktualis chat cim,
- jobb oldalon modellvalaszto es Frissites/Betoltes/Levalasztas/tema gomb,
- csak also border, nincs panel-kartya hatas.

Message area:

- teljes szeles scroll container,
- uzenetek kozepre koncentralt max szelessegu savban,
- assistant Markdown render,
- copy minden assistant valaszon,
- regenerate csak a legutolso assistant valaszon.

Composer:

- autosize textarea max magassagig,
- max utan belso scrollbar,
- textarea felfele no ki a 40px-es slotbol,
- chat input hattere `--color-surface`, border `--color-border`, radius `18px`, shadow nelkul,
- reasoning es send gomb mellette,
- warning slot alatta.

Button rendszer:

- primary: `#f18823`, hover `#ffaa29`, feher/on-primary text,
- secondary akciok alapbol csak szoveg/ikon, hoverre vilagos gombtest,
- dark mode-ban secondary alap text vilagosabb tokenbol jon.

## Inditas

Windowsbol:

```powershell
cd \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant
.\scripts\start.ps1
```

URL-ek:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

Logok:

```bash
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-backend.log
wsl -d Ubuntu-24.04 -u bober tail -f /tmp/ai-assistant-frontend.log
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

Legutobbi ismert allapot: frontend build sikeres. A teljes backend teszt/ruff ellenorzest nagyobb zaras elott erdemes ujrafuttatni.

## Kovetkezo logikus munka

- Teljes backend test + ruff futtatas.
- Manual smoke LM Studioval.
- UI finomhangolas mar csak kis lepesekben.
- `ChatShell.tsx` kesobbi komponensbontasa.
