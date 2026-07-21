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
- httpx LM Studio provider reteg opcionális API authentication headerrel; native es Responses API utakkal.
- Configbol valaszthato LLM provider reteg: `LLMProvider` Protocol, `get_llm_provider()` factory, `lm_studio_native` es kiprobalt `lm_studio_responses` provider; a helyi aktualis futas Responses providerrel mukodik.
- pytest/ruff dev stack.

Frontend:

- React + Vite + TypeScript.
- lucide-react.
- react-markdown + remark-gfm.
- Tokenizalt light/dark CSS.
- Legutobbi UI/performance polish blokk: composer/chatfolyam vizualis kozepszinkron, textarea shell, scrollbar finomitasok, also fade, scroll-to-bottom gomb, send gomb animacio, vegig lathato pending typing indicator, user buborek sortores/scrollbar finomitas, MessageThread memoizacio es recovery editor reszponzivitas.
- 2026-07-21 UI allapot: 50px-es kapszula composer, dedikalt composer capsule radius token tobb gombon/panelen, composer border arnyek nelkul, egységesebb oldalsav/menu/action padding, viewportba illeszkedo oldalsav context menu, 500-as/uppercase nelkuli gombtipografia, finomitott lila primary tokenek es finoman kiemelt empty-chat figyelmeztetes a Gondolkodo + Tudásbázis/Adatbázis kombinacio ellen.

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
- `backend/app/llm_provider.py` provider dataclassok, `LLMProvider` Protocol, `LMStudioNativeProvider`, `LMStudioResponsesProvider` skeleton, `get_llm_provider()` factory
- `backend/app/tool_modes.py`
- `backend/app/routers/assistant.py`
- `backend/app/routers/lm_studio.py`
- `backend/app/routers/health.py`

Frontend:

- `frontend/src/api/assistant.ts`
- `frontend/src/components/ChatShell.tsx` fo container es workflow state
- `frontend/src/components/ConversationRail.tsx` mentett chat lista
- `frontend/src/components/MessageThread.tsx` memoizalt uzenetlista, Markdown es recovery actionok
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
- `POST /api/lm-studio/select-chat-model` legacy, 410 Gone
- `POST /api/lm-studio/load-chat-model` legacy, 410 Gone
- `POST /api/lm-studio/unload-chat-model` legacy, 410 Gone
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
qwen/qwen3.5-9b
```

Load config defaultok `.env.example` szerint:

- context length: `61440`,
- eval batch size: `512`,
- flash attention: `true`,
- offload KV cache to GPU: `true`,
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
- Tudásbázis modban a provider request kapja az Obsidian integrations listat es a butitott magyar vault-only system promptot; a konkret 00-INDEX -> legrelevansabb jegyzetek -> dedikalt Kapcsolódó dokumentumok wikilink flow az aktualis user prompt call-frame-ben van, mert ezt a lokalis 9B modell stabilabban koveti.
- A Tudásbázis prompt app-oldali szerzodese: a system prompt csak a szerepet, vault-only tiltast, read-only modot es valaszstilust rogziti. A user call-frame mindig elolvastatja a 00-INDEX fajlt, kivalasztatja es kiolvastatja a legrelevansabb jegyzeteket, kotelezove teszi a jegyzetek vegen talalhato dedikalt Kapcsolódó dokumentumok szekcio wikilinkjeinek olvasasat, ha az elso jegyzetek nem pontosan a kerdesre vonatkozo informaciot tartalmazzak, es csak az osszes ilyen tovabbi jegyzet utan enged megbizhato valasz hianyat kimondani.
- Adatbázis modban a provider request kapja az Excel `integrations` listat es a read-only Excel system promptot.
- Az Adatbázis prompt app-oldali szerzodese index-router alapu: elso lepeskent `00-INDEX.xlsx` hasznalata, majd relevans Excel fajl/munkalap/tartomany/oszlop es read-only MCP eszkoz kivalasztasa.
- Az Adatbázis prompt letisztitott, 9B-barátabb magyar policy: kezeli a fajlnev-utalast, `00-INDEX.xlsx` alapjan fallback adatforrast valaszt, egyetlen `Toolhasználat` blokkban iranyitja a celzott read-only eszkozvalasztast, tiltja a hallucinaciot es az Excel irasi/mutacios muveleteket, beleertve pivot tabla, diagram, uj munkalap vagy seged-osszefoglalo letrehozasat. A tul eros munkafolyamat-tilto kor vissza lett egyszerusitve, mert a lokalis 9B-s modellnel rombolta a termeszetes eszkozhasznalatot.
- Az Excel MCP szerver konkret belso boviteset kulon munkamenet/projekt kezeli; ebben a repoban csak az app oldali tool mode szerzodest tartjuk nyilvan.
- Tudásbázis es Adatbázis egymast kizaro tool mode-ok; Gondolkodo barmelyikkel kombinalhato.
- A user prompt tisztan mentodik, tool prompt wrapper nem kerul DB user contentbe.
- Strukturalt Responses MCP/tool activity mentett UI-only artifactkent `tool_activity_content` mezobe kerulhet, de nem kerul vissza kovetkezo prompt history-ba.
- Manual smoke: LM Studio authentication + Obsidian MCP mellett a Tudásbázis mod vault-alapu valaszadasa mukodik; a butitott prompt es call-frame a felhasznaloi probaban bizonyult eddig a legstabilabbnak reasoning nelkul.
- Manual smoke: Excel MCP streamable-http szerverrel az Adatbázis mod Excel fajlbol stabilan valaszol.
- OpenAI-compatible kutatas es implementacio: a `/v1/responses` endpoint remote MCP formaban valodi strukturalt MCP/tool eventeket ad; a helyi app jelenleg Responses providerrel fut, explicit remote MCP tool URL-ekkel.

Excel MCP runtime jegyzet:

- Windows oldali venv: `C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\.venv`.
- Sandbox mappa: `C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\excel_files`.
- LM Studio endpoint: `http://127.0.0.1:8017/mcp`.
- Logutvonalak lokalisan, gitignore alatt: `.run_logs/local_mcp_notes.md`.

Reszletes doksik: implementation_plans/005_mcp_tool_modes_direction.md, implementation_plans/006_tool_mode_foundation_plan.md, implementation_plans/007_obsidian_tool_mode_plan.md, implementation_plans/009_excel_tool_mode_plan.md, implementation_plans/011_lm_studio_responses_mcp_notes.md, implementation_plans/012_llm_provider_abstraction_and_responses_provider.md, implementation_plans/013_obsidian_responses_remote_mcp_plan.md, implementation_plans/014_external_model_lifecycle_plan.md, implementation_plans/015_responses_tool_activity_artifacts.md.

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
- aktiv chat primary lila tokenbol jon,
- harompontos menu: Atnevezes, Torles; viewport aljan automatikusan felfele nyilik, hogy ne logjon ki.

Model panel:

- oldalsav tetejen kompakt modellallapot sor jelzi, hogy a konfiguralt modell betoltve van-e,
- a status es az aktualis chat cim kozott stabil, fenntartott notice hely van,
- a base URL mar nem jelenik meg a status sorban,
- jobb oldalon tema gomb; a frissites az oldalsav uj beszelgetes sora mellett van,
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
- stream kozben pending assistant buborek latszik; a typing indicator a teljes folyamat alatt megmarad, a mar erkezo tartalom alatt is jelzi az aktiv munkat,
- stop/hiba utan, ha az utolso message user marad, recovery action row jelenik meg: Szerkesztes es Ujrakuldes,
- Ujrakuldes nem duplikalja a user message-et, hanem arra streamel assistant valaszt,
- Szerkesztes inline textarea-val tortenik; autosize lefele no, alul tartja a chatfolyamot, ha a user eleve alul volt, nincs manual resize fogantyu, vizszintes scrollbar tiltott, scrollbar hover kurzor egyezik a composerrel,
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
- a fo chat scroll es a live reasoning panel is manual override-ot es stabil ResizeObserver/requestAnimationFrame alapu bottom-follow-t kapott: user felgorgetes eseten az auto-follow kikapcsol, aljara visszaterve ujra bekapcsol.

Composer:

- autosize textarea max magassagig,
- max utan belso scrollbar,
- textarea felfele no ki az 50px-es tokenizalt slotbol,
- a border/hatter/radius egy composer-textarea-shell hejon van, a tenyleges textarea belul border nelkul fut, hogy a belso scrollbar ne uljon bele a lekerekitett kulso ivbe,
- chat input 50px-es tokenizalt alapmagassagot es kapszula-radius tokent hasznal, hattere a user buborek surface tokenjehez igazodik, arnyek nelkul, 1px-es tokenizalt borderrel,
- desktopon es mobilon is van kulon Kuldes gomb; desktopon Enter is kuld, Shift+Enter sortorest ad,
- ures inputnal a Kuldes gomb vizualisan eltunik, tartalomnal jobbról becsuszik; stream kozben Leallitas allapotba valt es AbortControllerrel megszakitja az aktiv REST/SSE streamet,
- warning slot alatta.

Stop/cancel dontes:

- tudatosan maradunk az LM Studio REST API mellett,
- a Leallitas jelenleg connection-abort alapu: frontend `AbortController`, backend `StreamingResponse` generator es httpx stream context zaras,
- kulon LM Studio SDK-s `prediction.cancel()` integracio nincs bevezetve, mert nagyobb architekturalis valtas lenne.

Button rendszer:

- primary tokenek: light #2a007a / #5800ff, dark #5800ff / #7c37ff, feher/on-primary text,
- secondary akciok alapbol csak szoveg/ikon, hoverre vilagos gombtest,
- gombtipografia 500-as sulyu, uppercase nelkul, egységes radius-sm lekerekitessel; dark mode-ban secondary alap text vilagosabb tokenbol jon.
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

Legutobbi celzott allapot: backend tests/test_tool_modes.py - 9 passed; frontend npm run build - passed. A normal send, regenerate streaming, stop utani Ujrakuldes, inline Szerkesztes, recovery textarea finomitasok, reasoning delta UI, manual scroll override, saved reasoning disclosure, ChatShell hook-bontas, MessageThread render performance memoizacio, LM Studio API auth, Obsidian/Tudásbázis MVP, Excel/Adatbázis MVP, Responses tool activity, final-answer/work-narration szetvalasztas, Markdown layout hygiene es a legutobbi composer/chatfolyam/rail UI polish felhasznaloi proban/buildben mukodnek.

## Kovetkezo logikus munka

- A provider-abstraction, a kulso LM Studio modell-eletciklus es a Responses provideres tool activity artifact MVP kesz es felhasznaloi proban jonak itelt allapotban van.
- A helyi aktualis futas `lm_studio_responses` providerrel, konfiguralt `qwen/qwen3.5-9b` modellel mukodik; a modellt az LM Studio kezeli, az app csak allapotot jelez es betoltott konfiguralt modell mellett kuld.
- Az `Eszközhasználat` doboz strukturalt Responses MCP eventekbol epul, live es mentett allapotban is listás Markdownkent jelenik meg, es nem kerul vissza a modellkontextusba.
- Kovetkezo erdemi munka uj konkret funkcio, Excel/Obsidian prompt finomhangolas vagy hasznalati visszajelzes alapjan induljon; a legutobbi zaras kifejezetten Tudásbázis prompt call-frame es UI token/radius/padding polish volt.
- Parkolopalyan marad: stream status text, delta throttling, saved reasoning karakterhossz kijelzes, kulon reasoning/tool activity copy gomb, tool-call timeline, code block copy/language badge/syntax highlighting, MarkdownContent wrapper, wrap/nowrap kapcsolo.
- Nagyobb zaras elott ujra: `pytest -q`, `ruff check app tests`, `npm run build`.
