# AI Assistant Standalone

Ez a konyvtar mar egy mukodo standalone, lokalis AI chat webapp scaffold es implementacio alapja. Nem a BoberDetective projekt resze, nem hasznal BoberDetective domain funkciokat, es nem epit BoberDetective adatbazisra.

## Átfogó rendszer-dokumentáció

A teljes helyi AI-ökoszisztéma — Assistant, LM Studio, Obsidian/MCP, Excel MCP és GraphRAG — rendszerszintű műszaki leírása: [`system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md`](system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md).

Cel: altalanos, lokalis LM Studio chat alkalmazas mentett beszelgetesekkel, modellallapot-kezelovel es letisztult light/dark UI-val.

## Jelenlegi allapot

Megvalosult:

- FastAPI backend `/api` prefix alatt.
- PostgreSQL + SQLAlchemy + Alembic persistence.
- Kulon standalone Postgres kontener es volume: `ai-assistant-postgres`, `ai_assistant_postgres_data`.
- Host Postgres port: `56000`, amely elkulonul a BoberDetective `5432` es a GraphRAG `56001` portjatol, es kivul esik a Windows altal kizart `55432-55731` tartomanyon.
- React + Vite + TypeScript frontend.
- Configbol valaszthato LLM provider reteg: a sablon tovabbra is konzervativ `lm_studio_native`, a jelenlegi lokalis kiprobalt allapot `lm_studio_responses` providerrel fut.
- LM Studio provider health/list/chat endpointokkal es opcionális API authentication headerrel.
- Az appbol torteno modellvalasztas/load/unload es chatkuldes kozbeni auto-load kivezetve; a konfiguralt `qwen/qwen3.5-9b` modellt az LM Studio-ban kell betolteni.
- Mentett beszelgetesek, uj chat, rename, alapbol vegleges torles; soft delete configbol visszakapcsolhato.
- Streamelt uzenetkuldes, Markdown assistant valaszok, copy, csak legutolso assistant valasz streamelt ujrageneralasa.
- Stream kozben leallitas gomb; stop/hiba utan az utolso megvalaszolatlan user uzenet ujrakuldheto vagy inline szerkesztheto.
- Egysegesitett error/warning MVP: magyarabb hibak, composer warning helper es modellallapot hiba/warning sorok.
- Gondolkodo/reasoning kapcsolo `Lightbulb` / `LightbulbOff` ikonnal: Normal es GraphRAG modban engedelyezett; Tudásbázis/Obsidian es Adatbázis/Excel modban UI- es backend-oldalon is kikapcsolt.
- Tudásbázis/Obsidian tool mode: LM Studio MCP integration request-szintu engedelyezese, butitott magyar vault-only system prompt, 00-INDEX.md utvalaszto hasznalata, a konkret forrasfeltaro flow az aktualis user prompt call-frame-ben, dedikalt Kapcsolódó dokumentumok wikilinkek kontrollalt kovetese, user prompt tiszta mentese.
- Adatbázis/Excel tool mode: LM Studio MCP integration request-szintu engedelyezese, letisztitott index-router read-only Excel prompt policy, celzott toolhasznalat, user prompt tiszta mentese; tool modban az aktualis user prompt csak a modellhivasban kap rovid 00-INDEX-es call-frame keretet, DB/context szennyezes nelkul.
- GraphRAG mode: explicit user kapcsoloval, minden kérdésnél determinisztikusan meghívja a különálló GraphRAG Knowledge Service read-only `/v1/retrieve` API-ját, majd a validált, méretkorlátos és forráscímkézett evidence-et adja a chat modellnek; az Obsidian/Excel MCP módokkal kölcsönösen kizáró, reasoninggel kombinálható.
- Forrasmod-kontextus izolacio: Tudásbázis, Adatbázis es GraphRAG modban a teljes beszelgetes tovabbra is megmarad az adatbazisban es a UI-ban, de a modell minden send, retry es regenerate hivasnal csak az aktualis felhasznaloi uzenetet, az aktualis modpromptot es az aktualis forrasanyagot kapja meg. A normal chat valtozatlanul teljes elozmenyt hasznal.
- Belsőutasítás-védelem: mind a négy mód system promptja tiltja a rendszerprompt, fejlesztői utasítás, rejtett belső szabály és védelmi logika feltárását, módosítását vagy megkerülését; a Tudásbázis-, Adatbázis- és GraphRAG-wrapper ezt külön is megismétli. A felhasználónak dokumentált funkciók és használati útmutatók továbbra is válaszolhatók.
- Determinisztikus Sensitive Request és Output Guard: a request guard a modell- és forráshívás előtt blokkolja a nagy bizonyosságú belsőutasítás-, credential-, capability- és bypass kéréseket; az output guard kizárólag a felhasználónak megjelenő vagy mentett szövegcsatornákat vizsgálja gördülő stream-tartóablakkal. A nyers provider raw/status payload nem kliensoutput és nem vizsgált csatorna.
- Reasoning delta UI: `Gondolkodik` allapot, lenyithato `Gondolatmenet`, preview/expanded mod, Markdown render, whitespace normalizalas es user-respectful manual scroll override.
- Mentett reasoning artifactok: a backend `reasoning_content` mezoben megorzi a streaming reasoninget, a frontend alapbol csukott `SavedReasoningPanel` disclosure-kent mutatja, de a provider/context builder es a 120000 karakteres guard nem szamolja bele.
- Responses provider alatti MCP/tool activity artifactok: az `Eszközhasználat` doboz live es mentett allapotban is kulon, kekes disclosure-kent jelenik meg, `tool_activity_content` mezoben mentve, a chat contextbol kizart listás Markdown naploval; a live UI a backend által küldött sortöréseket változatlanul őrzi.
- Responses provider alatti final answer szetvalasztas: a vegleges assistant valasz az utolso strukturalt message itembol jon, az ezt megelozo modell-munkanarracio kulon Munkalepesek UI-only artifactkent mentodik es nem kerul vissza kontextusba.
- Explicit 120000 karakteres prompt/context vedelem frontend es backend oldalon.
- Light/dark tokenizalt UI.
- Legutobbi UI/performance polish zaras: composer/chatfolyam kozepszinkron, finomitott textarea shell, scrollbar kezeles, aljara ugras gomb, also fade, send gomb animacio, vegig lathato pending typing indicator, user buborek sortores/scrollbar finomitas, egységesített conversation rail sorritmus es hosszabb chatfolyam melletti MessageThread memoizacio.
- 2026-07-19 UI ráncfelvarrás: egységes color-page felület-háttér, árnyékmentes gomb/panel nyelv, chat action hoverhez igazított másodlagos gombok, kompaktabb radius-sm gomb-lekerekítés, letisztított composer/rename input focus-viselkedés, oldalsávba költöztetett modellállapot, egyesített frissítés művelet és egyszerűsített felső chat fejléc.
- 2026-07-20 UI finomitas: 50px-es tokenizalt composer alapmagassag, kapszula-radius token a composerhez es user buborek nagy sarkaihoz, finom composer arnyek, viewportba illeszkedo oldalsav context menu, valamint lazabb 500-as gomb tipografia uppercase nelkul.
- 2026-07-30 reasoning kompatibilitasi korlat: a Gondolkodo mod csak Normal es GraphRAG modban kapcsolhato be; Tudásbázis/Obsidian vagy Adatbázis/Excel valtasakor automatikusan kikapcsol, a gomb letiltott `not-allowed` kurzort kap, a backend pedig minden send/retry/regenerate uton `normal` reasoningra kenyszeriti a tiltott kombinaciot. Az ures chat indito szovege es a composer placeholder is ezt a letisztult viselkedest koveti.
- 2026-07-30 UI finomitas: az oldalsav chatcimei, context menu akcioi, dialogusakcioi es composer modvalasztoi celzottan 400-as sulyt hasznalnak, a modellallapot 700-as kiemelest kap. A torles dialogus alap/hover pirosa `#bb0000` / `#ff0000`, a streameles kozbeni harompontos indikator kapszulaja pedig magassagban teltebb.
- Windows/PowerShell indito, statusz es leallito scriptek.

Nem cel es nincs benne:

- case, document, OCR, Docling,
- saját RAG pipeline, Qdrant, Neo4j, embedding vagy extraction,
- a GraphRAG belső adatbázisainak vagy vaultjának közvetlen elérése,
- nyomozati objektumok,
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
    tool_modes.py
    graphrag_client.py
    graphrag_context.py
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
  start-services.sh
  status-services.sh
  stop-services.sh
```

## Inditas Windows PowerShellbol - STABIL, ELFOGADOTT MOD

Ezt hasznald. Ez a BoberDetective-nel bevalt WSL/PowerShell minta standalone valtozata, es Windowsbol tesztelve mukodik.

```powershell
powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu-24.04\home\bober\projects\AI_Assistant\scripts\start.ps1
```

A `scripts/start.ps1` a WSL-beli `scripts/start-services.sh` segedszkriptet inditja. A rutin:

1. elinditja a standalone PostgreSQL-t a `127.0.0.1:56000` hostporton,
2. megvarja, amig az adatbazis tenylegesen kesz, majd lefuttatja az Alembic migraciot,
3. a backend sajat `backend/` munkakonyvtarabol, a frontend pedig a projektgyokerbol indul,
4. mindket folyamatot teljesen levlasztja a PowerShell konzolrol es sajat PID/log fajlt vezet `/tmp/ai-assistant-*` alatt,
5. backend- es frontend-health ellenorzessel ter vissza a promptba.

A `status.ps1` rovid PostgreSQL/backend/frontend allapotot ad. A `stop.ps1` csak az AI Assistant sajat PID-jeit, Vite/Uvicorn folyamatait es Compose-keszletet allitja le; BoberDetective-et nem erinti.

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
AI_ASSISTANT_DATABASE_URL=postgresql+psycopg://ai_assistant:ai_assistant@localhost:56000/ai_assistant
AI_ASSISTANT_LLM_PROVIDER=lm_studio_native
AI_ASSISTANT_LM_STUDIO_BASE_URL=http://127.0.0.1:1234
AI_ASSISTANT_LM_STUDIO_CHAT_MODEL=qwen/qwen3.5-9b
AI_ASSISTANT_CONTEXT_CHAR_BUDGET=120000
AI_ASSISTANT_CHAT_DELETE_MODE=hard
AI_ASSISTANT_SENSITIVE_REQUEST_GUARD_ENABLED=true
AI_ASSISTANT_SENSITIVE_OUTPUT_GUARD_ENABLED=true
AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian
AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID=mcp/excel
AI_ASSISTANT_GRAPHRAG_BASE_URL=http://127.0.0.1:8080
AI_ASSISTANT_GRAPHRAG_SERVICE_TOKEN=
AI_ASSISTANT_GRAPHRAG_REQUEST_TIMEOUT_SECONDS=30
AI_ASSISTANT_GRAPHRAG_RESULT_LIMIT=10
AI_ASSISTANT_GRAPHRAG_CONTEXT_CHAR_BUDGET=60000
AI_ASSISTANT_GRAPHRAG_MAX_RESPONSE_BYTES=2097152
AI_ASSISTANT_GRAPHRAG_VAULT_ID=
# Optional, required when LM Studio API authentication is enabled:
AI_ASSISTANT_LM_STUDIO_API_TOKEN=
```

A két sensitive guard kapcsoló egymástól független. Módosításuk backend-újraindítás
után lép életbe; kikapcsolásuk nem érinti a prompt-policyt vagy az MCP read-only
allowlisteket.

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

Legutobbi teljes ellenorzes: backend pytest 126 passed, ruff passed, frontend build passed. A normal send, regenerate streaming, megvalaszolatlan user uzenet recovery flow, reasoning delta UI, saved artifactok, Obsidian/Tudásbázis, Excel/Adatbázis es az explicit GraphRAG mód rendben volt. A GraphRAG pozitív, negatív, reasoninges és szolgáltatásfüggetlenségi live smoke-ja sikeresen lefutott; GraphRAG kiesésnél a normál mód működött, a GraphRAG mód 503-at adott silent fallback nélkül.

## Következő irány

A provider-abstraction, a külső LM Studio modell-életciklus, a Responses tool activity artifact, a final answer / Munkalépések szétválasztása, a tool-mode call-frame és az explicit GraphRAG mód egyben működik. A helyi futás lm_studio_responses providerrel és qwen/qwen3.5-9b modellel történik.

A GraphRAG integráció jelenlegi szerződése: kizárólag explicit felhasználói módválasztás, publikus read-only POST /v1/retrieve API, szerveroldali Bearer token, szigorú válaszvalidálás, rendezett Sx evidence, determinisztikus no-evidence ág és biztonságos, korlátozott provenance. A kliens egyetlen próbálkozást tesz explicit timeouttal és válaszméret-korláttal; automatikus retry nincs. A GraphRAG, Tudásbázis és Adatbázis forrásmód kölcsönösen kizáró; a Gondolkodó kapcsoló csak Normál és GraphRAG móddal kompatibilis.

A következő érdemi lépés a két repó retrieval contractjának verziózott rögzítése és automatizált contract tesztje, majd a reasoning nélküli relevancia- és negatív kérdéskorpusz bővítése. Retry policy csak külön döntés és tesztelés után kerüljön a kliensbe. A részletes megvalósítás és elfogadási állapot az implementation_plans/019_graphrag_mode_integration_plan.md dokumentumban található.

Parkolópályán marad: saved reasoning karakterhossz kijelzés, külön reasoning/tool activity copy gomb, stream status text, delta throttling, tool-call timeline UI, code block copy/language badge/syntax highlighting, MarkdownContent wrapper és wrap/nowrap kapcsoló.
