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
- httpx LM Studio native provider opcionális API authentication headerrel.
- pytest/ruff dev stack.

Frontend:

- React + Vite + TypeScript.
- lucide-react.
- react-markdown + remark-gfm.
- Tokenizalt light/dark CSS.
- Legutobbi UI polish blokk: composer/chatfolyam vizualis kozepszinkron, textarea shell, scrollbar finomitasok, also fade, scroll-to-bottom gomb es send gomb animacio.

Infrastructure:

- WSL2 Ubuntu alatt fut a backend/frontend.
- Windows hoston fut az LM Studio.
- Backend LM Studio base URL default: `http://127.0.0.1:1234`.
- Ha LM Studio authentication aktiv, a backend `AI_ASSISTANT_LM_STUDIO_API_TOKEN` env ertekkel kuldi a Bearer tokent minden native API hivasra.
- Standalone Postgres host port: `55432`.
- Windows start/status/stop scriptek vannak.
- A stabil Windows inditas elfogadott: `scripts/start.ps1` harom egyszeru WSL parancsot futtat, koztuk 5 masodperc szunettel.

## Fobb fajlok

Backend:

- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/assistant_service.py`
- `backend/app/llm_provider.py`
- `backend/app/model_runtime.py`
- `backend/app/tool_modes.py`
- `backend/app/routers/assistant.py`
- `backend/app/routers/lm_studio.py`
- `backend/app/routers/health.py`

Frontend:

- `frontend/src/api/assistant.ts`
- `frontend/src/components/ChatShell.tsx` fo container es workflow state
- `frontend/src/components/ConversationRail.tsx` mentett chat lista
- `frontend/src/components/MessageThread.tsx` uzenetlista, Markdown es recovery actionok
- `frontend/src/components/Composer.tsx` chat input es kuldes/leallitas gomb
- `frontend/src/components/ComposerModeBar.tsx` Gondolkodo/Tudásbázis/Adatbázis mod kapcsolok
- `frontend/src/components/ModelPanel.tsx` chat/modell allapot panel
- `frontend/src/components/ChatDialogs.tsx` rename/delete dialogok
- `frontend/src/utils/notices.ts` kozos notice/error helper
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
- `POST /api/assistant/chats/{chat_id}/messages` non-streaming fallback
- `POST /api/assistant/chats/{chat_id}/messages/stream` normal send streaming
- `POST /api/assistant/chats/{chat_id}/regenerate` non-streaming fallback
- `POST /api/assistant/chats/{chat_id}/regenerate/stream` latest assistant regenerate streaming
- `POST /api/assistant/chats/{chat_id}/retry-last-user/stream` megvalaszolatlan utolso user uzenet ujrakuldese streaminggel
- `PATCH /api/assistant/chats/{chat_id}/messages/{message_id}` csak az utolso megvalaszolatlan user uzenet szerkesztesere

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
- szovegszin a --color-on-primary tokenbol jon.

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


## Tool mode / Tudásbázis es Adatbázis

Az MCP/tool mode MVP-k kozul ket konkret mod mukodik.

- Frontend `tool_mode`: `none`, `obsidian` vagy `excel`.
- UI label: `Tudásbázis` az Obsidian MCP-hez, `Adatbázis` az Excel MCP-hez.
- Backend registry: `backend/app/tool_modes.py`.
- Config: `AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID`, default `mcp/obsidian`.
- Config: `AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID`, default `mcp/excel`.
- LM Studio auth config: `AI_ASSISTANT_LM_STUDIO_API_TOKEN`, csak lokalis `.env` titok.
- Tudásbázis modban a provider request kapja az Obsidian `integrations` listat es a vault-only system promptot.
- Adatbázis modban a provider request kapja az Excel `integrations` listat es a read-only Excel system promptot.
- Az Adatbázis prompt app-oldali szerzodese index-alapu: elso lepeskent `00-INDEX.xlsx` hasznalata, majd a relevans Excel fajl/munkalap/tartomany/oszlop kivalasztasa.
- Az Adatbázis prompt tiltja az Excel irasi/mutacios muveleteket, beleertve pivot tabla, diagram, uj munkalap vagy seged-osszefoglalo letrehozasat.
- Az Excel MCP szerver konkret belso boviteset kulon munkamenet/projekt kezeli; ebben a repoban csak az app oldali tool mode szerzodest tartjuk nyilvan.
- Tudásbázis es Adatbázis egymast kizaro tool mode-ok; Gondolkodo barmelyikkel kombinalhato.
- A user prompt tisztan mentodik, tool prompt wrapper nem kerul DB user contentbe.
- Raw MCP/tool-call intermediate adat nincs mentve es nem kerul vissza kovetkezo prompt history-ba.
- Manual smoke: LM Studio authentication + Obsidian MCP mellett a Tudásbázis mod vault-alapu valaszadasa mukodik.
- Manual smoke: Excel MCP streamable-http szerverrel az Adatbázis mod Excel fajlbol stabilan valaszol.

Excel MCP runtime jegyzet:

- Windows oldali venv: `C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\.venv`.
- Sandbox mappa: `C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\excel_files`.
- LM Studio endpoint: `http://127.0.0.1:8017/mcp`.
- Logutvonalak lokalisan, gitignore alatt: `.run_logs/local_mcp_notes.md`.

Reszletes doksik: `implementation_plans/005_mcp_tool_modes_direction.md`, `implementation_plans/006_tool_mode_foundation_plan.md`, `implementation_plans/007_obsidian_tool_mode_plan.md`, `implementation_plans/009_excel_tool_mode_plan.md`.

## Frontend UI jelenlegi allapot

Layout:

- bal oldali conversation rail,
- jobb oldali chat canvas,
- felso model/status panel,
- belso message-thread scroll,
- also composer.

Conversation rail:

- `Új beszélgetés` primary gomb,
- refresh icon button, a conversation row harompontos gombjaval kozos 40px-es ikon oszlopritmusban,
- mentett chat lista kulon szekciokent, felso borderrel elvalasztva,
- chat sorok alapbol csendesek,
- hoverre secondary gombtest,
- aktiv chat primary narancs,
- harompontos menu: Atnevezes, Torles.

Model panel:

- bal oldalon egy sorban status: `Modell állapot: <állapot>`,
- a status es az aktualis chat cim kozott stabil, fenntartott notice hely van,
- a base URL mar nem jelenik meg a status sorban,
- jobb oldalon teljes szelessegu modellvalaszto es Frissites/Betoltes/Levalasztas/tema gomb,
- csak also border, nincs panel-kartya hatas,
- success notice-ok par masodperc utan eltunnek; warning/error notice-ok allapotfuggoen maradnak.

Message area:

- teljes szeles scroll container,
- uzenetek kozepre koncentralt max szelessegu savban,
- a fo chatfolyam scrollbarja szelesebb, konnyebben megfoghato; a composer vizualisan kompenzalja ennek kozeppont-eltereset,
- alul statikus fade reteg segiti a kifuto tartalom finomabb eltuneset,
- ha a user nincs legalul, megjelenik egy diszkret, feltranszparens scroll-to-bottom gomb; hoverre teljes primary szint kap, es a composer textarea magassagat kovetve marad a composer felett,
- assistant Markdown render,
- Markdown layout hygiene: code blockok es GFM tablazatok sajat horizontalis overflow-val maradnak a chat savon belul; inline code jelenlegi chip-szeru viselkedese elfogadott,
- normal send streaminggel epiti az assistant valaszt,
- regenerate streaminggel epiti ujra csak a legutolso assistant valaszt,
- stream kozben pending assistant buborek latszik; ures tartalomnal a typing indicator jelenik meg,
- stop/hiba utan, ha az utolso message user marad, recovery action row jelenik meg: Szerkesztes es Ujrakuldes,
- Ujrakuldes nem duplikalja a user message-et, hanem arra streamel assistant valaszt,
- Szerkesztes inline textarea-val tortenik; autosize lefele no, nincs manual resize fogantyu, vizszintes scrollbar tiltott,
- Mentes es kuldes menti a modositott user textet es ugyanarra indit streamelt assistant valaszt,
- copy minden vegleges assistant valaszon.

Reasoning panel:

- `reasoning_delta` eventek futas kozben live panelben jelennek meg, es sikeres `done` utan `reasoning_content` mezoben mentett artifactkent megmaradnak,
- a pending assistant bubble tetejen jelenik meg,
- alap felirat: `Gondolkodik`, lenyithato cim: `Gondolatmenet`,
- automatikus preview body par soros magassaggal,
- kattintasra expanded allapot nagyobb, de limitált magassaggal,
- uj reasoning delta erkezesekor a panel automatikusan az aljara gorget, de manual scroll override van: ha a user felgorget, nem rangatjuk vissza,
- Markdown rendereles es reasoning-only whitespace normalizalas van, hogy a modellek tul szellos gondolatmenete kompakt maradjon,
- `done` utan a live panel eltunik, de ha volt mentett reasoning, a vegleges assistant valasz folott csukott `Gondolatmenet` / `SavedReasoningPanel` disclosure jelenik meg,
- a mentett reasoning nem kuldodik vissza a modellnek es nem szamit bele a 120000 karakteres context guardba,
- DB mezo: `assistant_messages.reasoning_content`, migracio: `0002_saved_reasoning_content.py`,
- a fo chat scroll is manual override-ot kapott streaming kozben: user felgorgetes eseten az auto-follow kikapcsol, aljara visszaterve ujra bekapcsol.

Composer:

- autosize textarea max magassagig,
- max utan belso scrollbar,
- textarea felfele no ki a 40px-es slotbol,
- a border/hatter/radius egy composer-textarea-shell hejon van, a tenyleges textarea belul border nelkul fut, hogy a belso scrollbar ne uljon bele a lekerekitett kulso ivbe,
- chat input hattere surface token, alap border standard border token, focus border primary-border token, radius 18px, shadow nelkul,
- desktopon es mobilon is van kulon Kuldes gomb; desktopon Enter is kuld, Shift+Enter sortorest ad,
- ures inputnal a Kuldes gomb vizualisan eltunik, tartalomnal jobbról becsuszik; stream kozben Leallitas allapotba valt es AbortControllerrel megszakitja az aktiv streamet,
- warning slot alatta.

Button rendszer:

- primary: `#f18823`, hover `#ffaa29`, feher/on-primary text,
- secondary akciok alapbol csak szoveg/ikon, hoverre vilagos gombtest,
- dark mode-ban secondary alap text vilagosabb tokenbol jon.
- mobil nezethez a CSS fajl vegen egy kozos max-width 760px media query blokk tartozik.

## Inditas - stabil elfogadott mod

Windowsbol, barmelyik PowerShell mappabol:

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

A start script szandekosan csak harom WSL parancsot tartalmaz, koztuk 5 masodperc szunettel:

1. standalone Postgres + Alembic migracio,
2. backend kozvetlen `setsid -f` inditassal,
3. frontend kozvetlen `setsid -f` inditassal.

Ne tegyunk vissza portproxy-t, belso `sh -c` reteget vagy start elotti `pkill` parancsot. Ezek mar okoztak hibas inditast. A stop script felel a regi folyamatok leallitasert.

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

Legutobbi ismert allapot: `pytest -q` 40 passed, `npm --prefix frontend run build` passed, `git diff --check` tiszta. A normal send, regenerate streaming, stop utani Ujrakuldes, inline Szerkesztes, recovery textarea finomitasok, reasoning delta UI, manual scroll override, saved reasoning disclosure, ChatShell hook-bontas, LM Studio API auth, Obsidian/Tudásbázis MVP, Excel/Adatbázis MVP, Markdown layout hygiene es a legutobbi composer/chatfolyam/rail UI polish felhasznaloi proban/buildben mukodnek.

## Kovetkezo logikus munka

- Reasoning delta UI es saved reasoning artifact MVP kesz; tovabbi finomhangolas csak hasznalati visszajelzes alapjan. Reszletes tervek: `implementation_plans/003_reasoning_delta_ui.md`, `implementation_plans/004_saved_reasoning_artifacts.md`.
- ChatShell hook-bontas kesz: `useModelState`, `useThreadScrollFollow`, `useAutosizeTextarea`; tovabbi bontas csak uj funkcio vagy fajdalmas karbantartas eseten indokolt.
- Obsidian/Tudásbázis MVP es Excel/Adatbázis MVP mukodik; kovetkezo munka Excel file-kivalasztasi UX, uj konkret funkcio, Obsidian/Excel finomhangolas vagy mas hasznalati visszajelzes alapjan induljon.
- Parkolopalyan marad, nem elvetve: stream status text, delta throttling, saved reasoning karakterhossz kijelzes, kulon reasoning copy gomb, code block copy/language badge/syntax highlighting, MarkdownContent wrapper, wrap/nowrap kapcsolo.
- UI finomhangolas mar csak kis lepesekben, konkret hasznalati visszajelzes alapjan.
- Nagyobb zaras elott ujra: `pytest -q`, `ruff check app tests`, `npm run build`.
