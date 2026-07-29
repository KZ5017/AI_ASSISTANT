# Standalone AI Assistant Handoff

## Cel

A projekt egy teljesen fuggetlen, altalanos, lokalis AI chat webapp LM Studiohoz.

Nem BoberDetective modul kiszerelese, nem BoberDetective aloldal, es nem hasznal BoberDetective adatbazist. A referencia projektbol csak a kiprobalt backend/frontend mintak es UX dontesek voltak hasznalva.

## Hard boundary

Az Assistant általános lokális chatalkalmazás marad; nem kap BoberDetective domaint, brandet, case/document/OCR/Docling vagy nyomozati workflow-t, és nem épít BoberDetective adatbázisra.

A GraphRAG külön rendszer és külön repó. Az Assistant:

- nem épít saját indexing, extraction, entity-resolution vagy graph retrieval pipeline-t,
- nem éri el közvetlenül a GraphRAG PostgreSQL, Qdrant, Neo4j vagy Obsidian vault rétegeit,
- kizárólag a publikus, read-only POST /v1/retrieve API-t hívja,
- csak explicit felhasználói GraphRAG kapcsolás esetén hívja ezt az API-t,
- nem engedi együtt a GraphRAG, Tudásbázis és Adatbázis forrásmódot,
- a Gondolkodó kapcsolót a forrásmódoktól függetlenül kezeli,
- GraphRAG hiba esetén nem vált át csendben más módra,
- nem naplózza, perzisztálja vagy küldi kliensre a GraphRAG tokent, nyers választ vagy teljes evidence-et.

Ha a user dokumentumszöveget másol be normál módban, az sima chat input.

## Aktualis technikai allapot

Backend:

- FastAPI, SQLAlchemy, Alembic és PostgreSQL.
- httpx alapú, konfigurálható LM Studio provider réteg opcionális API authentication headerrel; native és Responses API utak.
- Konfigurálható LLMProvider port és get_llm_provider factory; a helyi futás lm_studio_responses providerrel működik.
- Külön, hitelesített GraphRAG HTTP kliens szigorú Pydantic válaszszerződéssel.
- Rendezett GraphRAG evidence compiler, determinisztikus no-evidence ág és biztonságos provenance.
- pytest/ruff dev stack.
- A teljes helyi AI-ökoszisztéma (Assistant, LM Studio, Obsidian/MCP, Excel MCP és GraphRAG) elkülönített, rendszerszintű műszaki dokumentációja az `system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md` fájlban található. Ez nem az Assistant belső specifikációját helyettesíti, hanem a komponensek közötti szerződéseket és üzemeltetési képet egészíti ki.

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
- Backend LM Studio base URL default: http://127.0.0.1:1234.
- Ha LM Studio authentication aktív, a backend az AI_ASSISTANT_LM_STUDIO_API_TOKEN env értékkel küldi a Bearer tokent.
- Standalone Postgres host port: 56000.
- A külön GraphRAG szolgáltatás alap címe: http://127.0.0.1:8080; saját service tokennel és saját runtime-mal rendelkezik.
- Az Assistant és a GraphRAG egymástól függetlenül indítható és állítható le. A GraphRAG hibája csak az explicit GraphRAG módot érintheti.
- Windows start/status/stop scriptek vannak; a stabil start három egyszerű WSL parancsot futtat, köztük 5 másodperc szünettel.

## Fobb fajlok

Backend:

- backend/app/config.py
- backend/app/db.py
- backend/app/models.py
- backend/app/schemas.py
- backend/app/assistant_service.py
- backend/app/llm_provider.py provider portok és LM Studio adapterek
- backend/app/tool_modes.py forrásmód registry és promptok
- backend/app/graphrag_client.py hitelesített, méretkorlátos, szigorúan validált retrieve kliens
- backend/app/graphrag_context.py rendezett evidence compiler és biztonságos provenance
- backend/app/routers/assistant.py
- backend/app/routers/lm_studio.py
- backend/app/routers/health.py

Frontend:

- frontend/src/api/assistant.ts
- frontend/src/components/ChatShell.tsx fő container és workflow state
- frontend/src/components/ConversationRail.tsx mentett chat lista
- frontend/src/components/MessageThread.tsx memoizált üzenetlista, Markdown, recovery actionök és mentett GraphRAG források
- frontend/src/components/Composer.tsx chat input és küldés/leállítás gomb
- frontend/src/components/ComposerModeBar.tsx Gondolkodó/Tudásbázis/Adatbázis/GraphRAG kapcsolók
- frontend/src/components/SavedGraphRAGSourcesPanel.tsx csukott, biztonságos GraphRAG provenance panel
- frontend/src/components/ModelPanel.tsx chat/modell állapot panel
- frontend/src/components/ChatDialogs.tsx rename/delete dialogok
- frontend/src/utils/notices.ts közös notice/error helper
- frontend/src/styles/tokens.css
- frontend/src/styles/app.css

Docs/state:

- README.md
- AGENTS.md
- STANDALONE_AI_ASSISTANT_HANDOFF.md
- system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md
- NEW_CHAT_START_PROMPT.md
- SMOKE_TEST.md
- WINDOWS_START.md
- implementation_plans/019_graphrag_mode_integration_plan.md

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

- role user / assistant / system,
- content és sequence index,
- reasoning mode, modell és token/meta mezők,
- reasoning_content és tool_activity_content mentett, de modellkontextusba vissza nem küldött artifactok,
- message_metadata.graphrag biztonságos GraphRAG provenance,
- timestamps.

A GraphRAG metadata a meglévő JSON message_metadata mezőt használja, ezért ehhez nem kellett új adatbázis-migráció. A nyers retrieval válasz és a teljes evidence nem mentődik. Soft delete esetén a chat nem jelenik meg az aktív listában, de az adatok nem törlődnek fizikailag.

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


## Forrásmódok: Tudásbázis, Adatbázis és GraphRAG

Az Assistant három, egymást kölcsönösen kizáró forrásmódot támogat: obsidian, excel és graphrag. A Gondolkodó kapcsoló mindháromtól független, ezért bármelyikkel kombinálható. A módot mindig a felhasználó választja ki; nincs kérdésalapú automatikus GraphRAG-routing.
A három forrásmód generálási kontextusa szándékosan fordulónként izolált. A teljes beszélgetés megmarad az adatbázisban és látható a felületen, de Tudásbázis, Adatbázis és GraphRAG módban a modell send, retry és regenerate esetén csak az aktuális felhasználói üzenetet, az aktuális mód system promptját/call-frame-jét és az aktuális forrásanyagot kapja meg. Korábbi user- és assistant-üzenet nem kerül a modell inputjába, ezért egy rövid visszakérdezés önmagában értelmeződik. Normál módban a teljes beszélgetési előzmény továbbra is a modell kontextusának része.
Mind a négy végső system prompt közös, kötelező belsőutasítás-védelmet kap: a rendszerprompt, fejlesztői utasítás, rejtett belső szabály, üzenetszerep, belső döntési logika és védelmi mechanizmus feltárását, módosítását vagy megkerülését udvariasan meg kell tagadni. Ez nem tiltja a felhasználó számára dokumentált funkciók, működési módok és használati útmutatók ismertetését. A Tudásbázis-, Adatbázis- és GraphRAG-wrapper ezt közvetlenül a felhasználói kérdés után megismétli; normál módban nincs külön wrapper.



Tudásbázis és Adatbázis módban az LM Studio Responses provider a konfigurált read-only Obsidian vagy Excel MCP-integrációt használja. Tudásbázis módban a provider fix Obsidian allowlistet küld: vault_list, vault_read, vault_get_document_map, search_query, search_simple, tag_list. Ez a prompt-policy mellett technikailag kizárja a chatfelületről a vault írását, módosítását, törlését, áthelyezését, parancsfuttatását és a fájlt esetleg létrehozó megnyitását. A konkrét MCP-szerverek életciklusa nem ennek a repónak a felelőssége.

Az Assistant determinisztikus Sensitive Request és Sensitive Output Guard réteget is használ. A request guard a user üzenet mentése és bármely modell-, MCP- vagy GraphRAG-hívás előtt blokkolja a nagy bizonyosságú belsőutasítás-, credential-, capability- és bypass kéréseket. Az output guard kizárólag a felhasználónak ténylegesen megjelenő vagy perzisztált message, reasoning, emberileg formázott tool activity és work narration csatornán ellenőrzi a konfigurált titkokat és hosszú belsőutasítás-részleteket. Az opaque provider raw/status payload nem felhasználói output: nem kerül SSE-be, perzisztenciába vagy outputvizsgálatba, mert belső request-metaadatai téves blokkolást okozhatnának. Streamben kis gördülő tartóablak működik; blokkoláskor `security_blocked` SSE esemény érkezik, assistant válasz nem mentődik, a user üzenet recovery folyamata megmarad. A kapcsolók: `AI_ASSISTANT_SENSITIVE_REQUEST_GUARD_ENABLED` és `AI_ASSISTANT_SENSITIVE_OUTPUT_GUARD_ENABLED`, alapból true, egymástól függetlenek.

GraphRAG módban az Assistant nem fér hozzá közvetlenül a GraphRAG PostgreSQL, Qdrant, Neo4j vagy vault rétegeihez. A backend minden send, retry és regenerate kérésnél friss, hitelesített POST /v1/retrieve hívást küld a külön GraphRAG szolgáltatásnak, majd a szigorúan validált választ rendezett, Sx címkéjű evidence blokkokká fordítja. A tiszta felhasználói kérdés mentődik; a prompt wrapper és a teljes evidence csak az aktuális modellhívás része, nem kerül vissza a beszélgetési előzménybe.

A GraphRAG kliens fix hybrid stratégiát, konfigurálható result limitet, 30 másodperces alap timeoutot és 2 MiB alap válaszméret-korlátot használ. Jelenleg nincs automatikus retry: egy hívás történik, a timeout, hálózati hiba és upstream 5xx 503-as Assistant hibává, az auth- és contractsértés 502-es hibává alakul, titok vagy nyers upstream payload nélkül. Nincs csendes visszaesés normál chatre vagy MCP módra.

Ha a retrieval nem ad használható evidence-et, a backend determinisztikus magyar választ ment és az LLM-et nem hívja meg. Ha van evidence, a lokális qwen/qwen3.5-9b modell kapja a GraphRAG system promptot, a tiszta kérdést és a dokumentumonként, forráspozíció szerint rendezett evidence blokkokat. A blokkok helyet, pontos idézetet, további találati és környezeti szöveget, kapcsolatokat, állításokat és gráfútvonalakat tartalmazhatnak.

Az asszisztensüzenet message_metadata.graphrag mezőjében csak biztonságos provenance marad meg: query azonosító és típus, reason code, korlátozott warningok, truncation jelzés és legfeljebb 50 forrásleíró. A service token, a nyers GraphRAG válasz és a teljes evidence nem perzisztálható és nem kerülhet a frontendbe. A SavedGraphRAGSourcesPanel alapból csukott, az Sx címkéket, fájlútvonalat/címsorokat és biztonságos obsidian linkeket mutatja.

A GraphRAG rendszer külső, önálló runtime a /home/bober/projects/graphrag_system repóban. Az Assistant csak a publikus, read-only retrieve API szerződését ismeri. Részletes terv és elfogadási napló: implementation_plans/019_graphrag_mode_integration_plan.md.

Excel MCP runtime jegyzet:

- Windows oldali venv: C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\.venv.
- Sandbox mappa: C:\Users\KZsolt\SELF_WORK_DIR\Excel_MCP_Server\excel-mcp-server\excel_files.
- LM Studio endpoint: http://127.0.0.1:8017/mcp.
- Logútvonalak lokálisan, gitignore alatt: .run_logs/local_mcp_notes.md.
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

Legutóbbi teljes ellenőrzési alapállapot: backend pytest 120 passed, ruff passed, frontend build passed. Az explicit GraphRAG mód pozitív, negatív, reasoninges és szolgáltatásfüggetlenségi live smoke-ja sikeresen lefutott. GraphRAG kiesésnél a normál, Tudásbázis és Adatbázis mód működése független marad; GraphRAG módban nincs csendes fallback.

## Következő logikus munka

- A GraphRAG integráció MVP kész: explicit felhasználói kapcsoló, hitelesített külső retrieve hívás, strukturált evidence, biztonságos provenance és forráspanel működik.
- Következő érdemi lépés a két repó közötti retrieval contract verziózott rögzítése és automatizált contract tesztje.
- Érdemes bővíteni a relevancia- és negatív kérdéskorpuszt a friss GraphRAG projekción, különösen reasoning nélküli qwen/qwen3.5-9b futásokkal.
- A kliens jelenleg egyetlen próbálkozást tesz, explicit timeouttal; retry policy csak külön döntés és tesztelés után kerüljön bele.
- Kötelezően megmarad az explicit routing, a három forrásmód kölcsönös kizárása és a két rendszer önálló indíthatósága/leállíthatósága.
- Parkolópályán marad: stream status text, delta throttling, saved reasoning karakterhossz kijelzés, külön reasoning/tool activity copy gomb, tool-call timeline, code block copy/language badge/syntax highlighting, MarkdownContent wrapper és wrap/nowrap kapcsoló.
- Nagyobb zárás előtt újra: pytest -q, ruff format --check app tests, ruff check app tests és npm run build.
