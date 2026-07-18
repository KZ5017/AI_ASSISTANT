# Standalone AI Assistant Implementation Plan / Current Status

Ez a fajl mar nem indulasi tervkent, hanem aktualis allapotkovetokent olvasando.

## Product boundary

A standalone app altalanos lokalis LM Studio chat app. Tovabbra sem tartalmazhat BoberDetective domain funkciokat:

- case/document/RAG/Qdrant/source reference/OCR/Docling nincs,
- nyomozati objektumok es audit/provenance workflow nincs,
- BoberDetective brand nincs,
- BoberDetective adatbazisra nem epit.

## Phase status

### Phase 1 - Minimal scaffold

Status: kesz.

- Backend FastAPI scaffold kesz.
- Frontend Vite/React/TypeScript scaffold kesz.
- Docker Compose PostgreSQL kesz.
- Windows PowerShell indito/status/stop scriptek keszek.
- A stabil start script Windowsbol tesztelve mukodik: infra+migracio, 5 mp szunet, backend `setsid -f`, 5 mp szunet, frontend `setsid -f`.

### Phase 2 - LM Studio provider

Status: kesz, mukodo szerzodesekkel.

Megvan:

- Settings LM Studio base URL, chat model, timeout, context length, eval batch, flash attention, KV cache offload, auto-load, temperature, max output tokens, opcionális API token.
- Native `/api/v1/models`, `/api/v1/models/load`, `/api/v1/models/unload`, `/api/v1/chat` hasznalat.
- Health/list/select/load/unload/chat backend endpointok.
- Runtime selected chat model state.
- Auto-load chat hivas elott, ha engedelyezett.
- Reasoning mapping: UI `normal` -> provider `off`, UI `model_default` -> provider `model_default`.
- Opcionális LM Studio API authentication: ha `AI_ASSISTANT_LM_STUDIO_API_TOKEN` be van állítva, a provider minden native API kéréshez `Authorization: Bearer ...` headert küld.

Nincs es ne is legyen: embeddings/RAG.

### Phase 3 - Assistant persistence

Status: kesz.

Megvan:

- Assistant chat tabla.
- Assistant message tabla.
- Soft delete.
- Sequence index.
- JSON metadata mezok.
- Alembic migration.

### Phase 4 - Assistant backend service

Status: kesz.

Megvan:

- default title: `Uj beszelgetes` / UI-ban magyar cim,
- create chat,
- list active chats,
- get active chat detail,
- rename,
- soft delete,
- send message,
- stream send message,
- regenerate latest assistant message,
- stream regenerate latest assistant message,
- context budget guard,
- minimal system prompt,
- first user message based title,
- LLM provider error mapping.

### Phase 5 - Assistant API

Status: kesz.

Endpointok:

- `GET /api/assistant/status`
- `GET /api/assistant/chats`
- `POST /api/assistant/chats`
- `GET /api/assistant/chats/{chat_id}`
- `PATCH /api/assistant/chats/{chat_id}`
- `DELETE /api/assistant/chats/{chat_id}`
- `POST /api/assistant/chats/{chat_id}/messages`
- `POST /api/assistant/chats/{chat_id}/regenerate`

### Phase 6 - Frontend API client

Status: kesz.

`frontend/src/api/assistant.ts` tartalmazza az assistant es LM Studio szerzodeseket.

### Phase 7 - Frontend componentization

Status: elso kor kesz.

A fo UI elso komponensbontasa megtortent. A `ChatShell.tsx` tovabbra is tartalmazza a fo allapot- es workflow-logikat, de a nagyobb prezentacios blokkok kulon komponensekbe kerultek:

- conversation rail,
- model panel,
- message thread,
- composer,
- dialogs.

### Phase 8 - UI baseline

Status: kesz es iterativan finomitva.

Megvan:

- left rail + right chat canvas,
- belso message-thread scroll,
- pending user message,
- typing indicator,
- Markdown assistant rendering,
- copy/regenerate,
- reasoning toggle,
- standard kuldes: desktopon Enter kuld es Shift+Enter sortorest ad; mobilon kulon send gomb is van,
- autosize composer,
- stable warning slot,
- modellallapot panel,
- model select/load/unload.

Aktualis fontos UI dontesek:

- Primary szin: `#f18823`.
- Primary hover: `#ffaa29`.
- Secondary akciok alapbol szovegesek/ikonosak, hoverre kapnak gombtestet.
- Chat input surface hatteru, borderes, 18px radiusu, shadow nelkuli.
- Composer warning a beviteli mezo alatt fix helyen jelenik meg.
- Gondolkodo gomb send-button csaladba tartozik, inaktivan halvany, aktivan teljes primary.
- Mentett chat lista tetejen border valasztja el a rail headertol.

### Phase 9 - Theme/token system

Status: kesz alap.

Megvan:

- `tokens.css` light/dark tokenekkel,
- primary, secondary action text, surface, border, danger/warning/success tokenek,
- radius/spacing/shadow tokenek,
- dark mode `data-theme="dark"` alapon.

### Phase 10 - Tests and verification

Status: kesz az aktualis backend/tool-mode zarashoz.

Megvan:

- backend pytest testek assistant persistence, health, LM provider, LM Studio API, streaming es tool mode temakban,
- frontend `npm run build` sikeresen fut a legutobbi frontend zaras szerint,
- ruff ellenorzes sikeres a legutobbi lint zaras szerint.

Legutobbi ismert ellenorzes:

- `cd backend && .venv/bin/python -m pytest -q`: 40 passed, 1 ismert Starlette/httpx deprecation warning korabbi nagyobb zaraskor.
- `cd backend && .venv/bin/python -m pytest tests/test_tool_modes.py`: 7 passed az aktualis Excel prompt visszaegyszerusites utan.
- `npm --prefix frontend run build`: passed.
- `git diff --check`: passed.

### Phase 11 - LM Studio streaming responses

Status: kesz.

Megvan:

- LM Studio native `/api/v1/chat` streaming provider tamogatas,
- backend SSE parser es `LLMStreamEvent`,
- app-szintu SSE contract: `start`, `delta`, `reasoning_delta`, `status`, `error`, `done`,
- normal send streaming endpoint: `POST /api/assistant/chats/{chat_id}/messages/stream`,
- regenerate streaming endpoint: `POST /api/assistant/chats/{chat_id}/regenerate/stream`,
- frontend `fetch()` + `ReadableStream` SSE parser,
- normal send pending user + pending assistant flow,
- regenerate pending assistant flow,
- DB-be csak vegleges assistant valasz kerul `done` utan,
- non-streaming endpointok megmaradtak fallbacknek.

Manual allapot:

- A felhasznalo Windows bongeszobol kiprobalta, eddig jonak tunik.
- A backend es frontend ujrainditva, listener smoke sikeres: frontend `/` 200, `/api/assistant/status` ready 120000 budgettel.

### Phase 12 - Unanswered last user recovery

Status: F1, F2 es F3 kesz az aktualis recovery zarashoz.

Cel:

- Normal send stream stop/hiba utan elofordulhat, hogy az utolso chat message `user`, es nincs assistant valasz.
- Ezt nem toroljuk automatikusan.
- Az utolso megvalaszolatlan user uzenethez recovery akciok kellenek: `Újraküldés`, majd inline `Szerkesztés`.

Harom lepes:

1. F1: detektalas + `POST /api/assistant/chats/{chat_id}/retry-last-user/stream` + frontend `Újraküldés` action.
2. F2: inline szerkesztes + guarded backend update + `Mentés és küldés`.
3. F3: recovery UX polish, manual smoke, allapotfajlok frissitese - kesz.

Reszletes terv: `implementation_plans/001_lm_studio_streaming_responses.md`, Phase F.

### Phase 13 - Error/notice UX

Status: MVP kesz.

Megvan:

- kozos frontend notice/error helper: `frontend/src/utils/notices.ts`,
- strukturalt `AppNotice` tipus `info` / `success` / `warning` / `error` kategoriakkal,
- gyakori technikai hibak magyarabb normalizalasa,
- composer warning szabalyok kulon helperben,
- stream/abort hiba-polish: stop nem jelenik meg globalis hibakent,
- modellpanel success/warning/error notice-ok tipizalasa,
- modellpanel success notice-ok automatikus eltuntetese,
- modellpanel notice stabil, fenntartott helyen jelenik meg a status sor es a chat cim kozott.

Reszletes terv: `implementation_plans/002_error_notice_ux.md`.


### Phase 14 - Reasoning delta UI

Status: MVP kesz, felhasznaloi proban jonak itelve.

Megvan:

- frontend `ReasoningPanel.tsx` komponens,
- `reasoning_delta` stream eventek megjelenitese normal send, regenerate, retry es edit+send flow-ban,
- live reasoning runtime state streaming kozben,
- `Gondolkodik` allapot es `Gondolatmenet` panel,
- automatikus preview allapot par soros magassaggal,
- user altal lenyithato expanded allapot,
- automatikus aljara gorgetes, hogy a legfrissebb reasoning sorok latszodjanak, manual scroll override-dal, ha a user kozben felgorget,
- Markdown rendereles `react-markdown` + `remark-gfm` alapon,
- reasoning-only whitespace normalizalas a modellek tul szellos gondolatmenetenek tomoritesere,
- done utan a live reasoning panel eltunik, de ha volt reasoning tartalom, a vegleges assistant uzenethez mentett artifactkent kapcsolodik.

Reszletes terv es zaro dontesek: `implementation_plans/003_reasoning_delta_ui.md`.

### Phase 15 - Saved reasoning artifacts es scroll override

Status: MVP kesz, felhasznaloi proban jonak itelve.

Megvan:

- Alembic migracio: `0002_saved_reasoning_content.py`, `assistant_messages.reasoning_content` nullable TEXT oszloppal,
- backend streaming buffereli a `reasoning_delta` chunkokat es sikeres `done` utan `reasoning_content` mezobe menti,
- normal send, regenerate es retry stream flow menti a reasoninget, ha erkezett,
- `reasoning_content` nem kerul be a provider history payloadba, es a 120000 karakteres context guard sem szamolja,
- ures/whitespace-only reasoning `None`/null marad, tul hosszu reasoning 100000 karakterig vedett,
- frontend API tipus bovult `reasoning_content` mezovel,
- `SavedReasoningPanel.tsx` alapbol csukott, egysoros `Gondolatmenet` disclosure-kent jelenik meg a vegleges assistant valasz folott,
- lenyitva ugyanazt a kompakt Markdown/whitespace normalizalt megjelenitest hasznalja,
- live `ReasoningPanel` es fo chat scroll user-respectful manual override-ot kapott: ha a user felgorget stream kozben, az auto-follow nem rangatja vissza, aljara visszaterve ujra bekapcsol.

Ellenorzes:

- `pytest -q`: 32 passed, 1 ismert Starlette/httpx deprecation warning,
- `ruff check app tests`: passed,
- `npm run build`: passed,
- `git diff --check`: tiszta,
- Alembic migracio lefutott a lokalis standalone DB-n,
- backend es frontend ujrainditva, HTTP smoke: frontend `/` 200, backend `/docs` 200,
- DB-ben az `assistant_messages.reasoning_content` oszlop ellenorizve,
- felhasznaloi proban a saved reasoning disclosure lathato es jonak itelve.

Reszletes terv: `implementation_plans/004_saved_reasoning_artifacts.md`.

### Phase 16 - ChatShell hook-bontas es parked optional polish

Status: kesz.

Cel:

- A jelenlegi UI es streaming/reasoning funkciok stabilak, innen varhatoan uj termekfunkciok jonnek.
- Emiatt erdemes volt a `ChatShell.tsx` nagy workflow komponensbol nehany stabil, ujrahasznalhato hookot kivenni, de a jol mukodo streaming flow-t nem bolygatni feleslegesen.

Megvan:

- `frontend/src/hooks/useModelState.ts`: LM Studio health/model list/select/load/unload allapot es notice logika,
- `frontend/src/hooks/useThreadScrollFollow.ts`: fo chat scroll auto-follow + manual override,
- `frontend/src/hooks/useAutosizeTextarea.ts`: composer es recovery editor autosize logika,
- `ChatShell.tsx` tovabbra is a fo chat workflow orchestration helye, de kisebb es tisztabb lett,
- `MessageThread.tsx` ref tipus pontositas a hookbol erkezo thread refhez.

Ellenorzes:

- `npm run build`: passed.

Parkolopalyara tett opcionális polish:

- stream kozbeni status text,
- delta throttling,
- saved reasoning karakterhossz kijelzes,
- kulon reasoning copy gomb.

Ezek nincsenek elvetve, csak nem reszei a most veglegesnek tekintett tervallapotnak.


### Phase 17 - MCP/tool mode foundation es Obsidian Tudásbázis mód

Status: MVP kesz, felhasznaloi smoke szerint mukodik.

Megvan:

- iranykijelolo MCP/tool mode alapvetes: `implementation_plans/005_mcp_tool_modes_direction.md`,
- kozos tool mode foundation terv: `implementation_plans/006_tool_mode_foundation_plan.md`,
- Obsidian-specifikus implementacios terv: `implementation_plans/007_obsidian_tool_mode_plan.md`,
- backend `tool_modes.py` registry `none` es `obsidian` moddal,
- `AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID` config default `mcp/obsidian` ertekkel,
- opcionális `AI_ASSISTANT_LM_STUDIO_API_TOKEN` config LM Studio API authenticationhoz,
- provider-szintu Bearer token header minden LM Studio native API hivasra, ha token be van allitva,
- provider `integrations` payload tamogatas stream es non-stream chat hivasban,
- Obsidian/Tudásbázis modban Excel-prompt mintajara egyszerusitett magyar vault-only prompt policy a system contextben, `00-INDEX.md` utvalaszto hasznalattal, user text szennyezese nelkul,
- frontend composer mode sor: Gondolkodo + Tudásbázis kapcsolo,
- Tudásbázis tooltip aktiv/inaktiv allapottal,
- manual smoke: LM Studio authentication + Obsidian MCP mellett a Tudásbázis mod vault-alapu valaszadasa mukodik; a prompt finomitva lett, hogy reasoning nelkul se altalanos Obsidian/MCP leirast adjon, hanem a vault jegyzeteibol dolgozzon.

Fontos dontesek:

- az LM Studio authentication provider-szintu keresztmetszeti szerzodes, nem Obsidian-specifikus hack,
- a token csak lokalis `backend/.env` titok; `.env.example` csak ures kulcsot tartalmaz,
- a frontend tovabbra sem kuld nyers LM Studio `integrations` listat,
- raw MCP/tool-call intermediate adatot nem mentunk es nem adunk vissza kovetkezo prompt history-ba.

Ellenorzes:

- `pytest -q`: 40 passed, 1 ismert Starlette/httpx deprecation warning,
- `npm --prefix frontend run build`: passed,
- `git diff --check`: tiszta.


### Phase 18 - Markdown content layout hygiene

Status: CSS-only MVP kesz, felhasznaloi proban megfelelonek itelve.

Megvan:

- assistant Markdown block elemek celzott CSS kezelese,
- fenced code block / `pre code` horizontalis overflow vedelme,
- GFM table horizontalis overflow vedelme,
- heading/lista/blockquote/link/kep alapstilusok,
- inline code chip-szeru/monospace vizualis stilusa agressziv tordeles nelkul,
- user bubble tordelese megmaradt,
- reasoning panel kompakt Markdown stilusa nem lett bolygatva.

Tudatos dontes:

- a jelenlegi inline code, code block es table viselkedes megfelelo, ezert az MVP-t nem felbehagyott allapotnak, hanem lezart alapallapotnak tekintjuk,
- code block copy gomb, language badge, syntax highlighting, `MarkdownContent` wrapper es wrap/nowrap kapcsolo parkolopalyan marad, nem elvetve.

Ellenorzes:

- `npm run build`: passed,
- `git diff --check`: tiszta.

Reszletes terv es zaro dontesek: `implementation_plans/008_markdown_content_layout_hygiene.md`.

### Phase 19 - Composer/chatfolyam UI polish

Status: kesz, felhasznaloi proban jonak itelve.

Megvan:

- send/stop gomb csak ikon maradt, teljesen kerek primary gombkent,
- ures inputnal a send gomb vizualisan eltunik, tartalomnal jobbról becsuszik es helyet csinal maganak,
- typing indicator kisebb, narancsosabb, border nelkuli kapszula, es pending assistant alatt vegig lathato, amig a teljes valasz meg nem erkezik,
- composer textarea kulso composer-textarea-shell hejat kapott: hatter/radius/shadow a hejon, belso textarea border nelkul, igy a belso scrollbar nem ul bele a lekerekitett kulso ivbe,
- textarea es user bubble border nelkuliek; modell select kattintasra nem valt narancs borderre, az OS/browser alap select viselkedese nincs tulstilizalva,
- user bubble jobb also sarka kisebb radiusu, dark mode-ban surface-soft hatterrel, belso scrollbarja beljebb tartva, rovid szavak szettorese nelkul,
- chatfolyam aljan statikus fade reteg van,
- scroll-to-bottom gomb megjelenik, ha a user nincs legalul; kozepen lebeg, feltranszparens primary alapszinnel, hoverre teljes primaryvel,
- scroll-to-bottom gomb a composer textarea aktualis magassagat koveti, igy tobb soros inputnal is a composer felett marad,
- fo chatfolyam scrollbarja szelesebb es konnyebben megfoghato,
- composer/chatfolyam max szelesseg es vizualis kozeppont ossze lett hangolva a szelesebb chat scrollbar kompenzaciojaval,
- frontend useThreadScrollFollow hook kiadja az isThreadAtBottom allapotot es smooth scroll-to-bottom helperkent is hasznalhato.

Ellenorzes:

- npm run build: passed,
- git diff --check: tiszta.

### Phase 20 - Excel/Adatbázis tool mode MVP

Status: MVP kesz, LM Studio es app oldali felhasznaloi proban stabilnak itelve.

Megvan:

- Excel/Adatbázis implementacios terv: `implementation_plans/009_excel_tool_mode_plan.md`,
- valasztott MCP server: `haris-musa/excel-mcp-server`, Windows oldali venv-ben telepitve,
- Excel MCP streamable-http modban elindithato, `127.0.0.1:8017/mcp` endpointtal,
- LM Studio `mcp.json` kiegeszites utan az Excel MCP-t elerhetonek latja,
- manual LM Studio smoke: olvasasi promptokkal Excel fajlbol korrekt valaszokat ad,
- backend config: `AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID`, default `mcp/excel`,
- backend `tool_modes.py` registry `excel` moddal es letisztitott, index-router alapu, szigoru read-only Excel prompt policy-val; a Toolhasználat blokk celzott eszkozvalasztast ker, de nem tartalmaz domain-specifikus keresesi szabalyokat, es a tul eros munkafolyamat-tilto promptkor vissza lett egyszerusitve,
- API schema es frontend type bovult `tool_mode: "excel"` ertekkel,
- frontend composer mode sorban `Adatbázis` gomb van,
- `Tudásbázis` es `Adatbázis` egymast kizaro tool mode-ok, a `Gondolkodó` tovabbra is kombinalhato barmelyikkel,
- user prompt tisztan mentodik; Excel instrukciok csak provider request system contextben jelennek meg,
- raw MCP/tool-call intermediate adatot tovabbra sem mentunk es nem adunk vissza kovetkezo prompt history-ba.

Fontos MVP dontesek:

- fajlnev-utalas eseten a prompt eloszor a `00-INDEX.xlsx` fajllistaban probal egyertelmu talalatot keresni; ha nincs egyertelmu talalat, az index alapjan valaszt legjobb adatforrast,
- nincs file picker UI es nincs automatikus workbook discovery,
- az Adatbázis mod read-only: iras/modositas/formazas/torles tiltva system policy szinten akkor is, ha a user erre ker,
- az LM Studio UI-ban lathato tool kapcsolok hasznosak lehetnek, de az app MVP-je nem tekinti oket garancialis API oldali kontrollnak.

Ellenorzes:

- `pytest -q`: 40 passed, 1 ismert Starlette/httpx deprecation warning,
- `npm --prefix frontend run build`: passed,
- `git diff --check`: tiszta,
- backend es frontend ujrainditva,
- felhasznaloi smoke: Excel/Adatbázis mod stabilan valaszol; a letisztitott index-router + Toolhasználat prompt jelentosen javitotta a viselkedest.

### Phase 21 - Conversation rail UI polish

Status: kesz, felhasznaloi proban tokeletesnek itelve.

Megvan:

- rail header es conversation row kozos 40px ikon oszlopot es 40px sorritmust kapott,
- refresh gomb es harompontos conversation menu gomb merete osszhangba kerult,
- `Új beszélgetés` primary gomb felirata magyarabb es kozepre igazított maradt,
- conversation lista megorizte a kulon szekcio/border elvalasztast.

Ellenorzes:

- `npm --prefix frontend run build`: passed,
- felhasznaloi UI smoke: megfelelo.


### Phase 22 - Chat thread render performance es recovery editor polish

Status: kesz, felhasznaloi proban erezhetoen javult.

Megvan:

- reszletes performance terv: `implementation_plans/010_chat_thread_render_performance.md`,
- `useStableCallback` hook a message thread action callbackok stabilizalasara,
- `historyCharCount` memoizalasa, hogy composer gepeleskor ne jarja be ujra a teljes chat historyt,
- `MessageThread` memo vedelme,
- `MessageItem` szintu memoizacio, hogy inline user-bubble szerkeszteskor csak az erintett sor renderelodjon ujra,
- `useAutosizeTextarea` `useLayoutEffect`-re valtott, hogy paste/tobbsoros novekedes elott merje a textarea magassagat,
- recovery editor alul tartja a chatfolyamot, ha a user eleve alul volt, de nem rangatja vissza, ha a user felgorgetett,
- recovery editor scrollbar hover kurzora egyezik a composer textarea scrollbar viselkedesevel, a renderelt user buborek pedig belso scrollt es normalis szotorest kapott.

Tudatos stop/cancel dontes:

- maradunk LM Studio REST/SSE streamen,
- a Leallitas `AbortController` + connection-abort alapu,
- kulon LM Studio SDK-s `prediction.cancel()` integracio most nem kerul be, mert nagyobb architekturalis valtas lenne.

Ellenorzes:

- `npm --prefix frontend run build`: passed,
- `git diff --check`: tiszta.

### Phase 23 - LM Studio `/v1/responses` + MCP kutatasi jegyzet

Status: kutatasi jegyzet kesz, nem implementacios terv.

Megallapitasok:

- `/v1/chat/completions` custom tool callingot tud, de nem kezeli az LM Studio `mcp.json` integraciokat ugy, mint a nativ `/api/v1/chat`,
- `/v1/responses` remote MCP formaban valodi strukturalt MCP eventeket ad (`mcp_list_tools`, `mcp_call`, tool output, reasoning, final message),
- a mukodo forma explicit `tools: [{ type: "mcp", server_url: "http://127.0.0.1:8017/mcp" }]`,
- az `integrations: ["mcp/excel"]` forma `/v1/responses` alatt nem bizonyult mukodonek,
- rovid tavon nem valtunk providert; a jelenlegi app marad a nativ LM Studio `/api/v1/chat` uton.

Reszletek: `implementation_plans/011_lm_studio_responses_mcp_notes.md`.

### Phase 24 - LLM provider abstraction es Responses provider terv

Status: implementacios terv kesz, kod nincs meg.

Cel:

- a jelenlegi stabil `lm_studio_native` provider maradjon default es erintetlen mukodesi alap,
- configbol lehessen kesobb providert valtani,
- az assistant service es frontend SSE szerzodes maradjon provider-fuggetlen,
- a `/v1/responses` + remote MCP ut kulon providerkent legyen bevezetve, nem a mostani native ut helyett.

Kovetkezo kodos lepes a terv szerint: F1 - provider interface + factory, `AI_ASSISTANT_LLM_PROVIDER=lm_studio_native` defaulttal, viselkedesvaltozas nelkul.

Reszletek: `implementation_plans/012_llm_provider_abstraction_and_responses_provider.md`.

## Kovetkezo logikus lepesek

1. A provider-abstraction terv kesz; kovetkezo kodos lepeskent a `012` terv F1 kore javasolt: provider interface + factory, `AI_ASSISTANT_LLM_PROVIDER=lm_studio_native` defaulttal, viselkedesvaltozas nelkul.
2. Obsidian/Tudásbázis MVP szigoritott magyar vault-only prompttal, Excel/Adatbázis MVP letisztitott index-router + Toolhasználat prompttal, a `/v1/responses` + remote MCP kutatasi jegyzet, a composer/chatfolyam/rail UI polish blokk es a chat thread render performance kor mukodik; tovabbi munka uj konkret funkcio, Excel file-kivalasztasi UX, Obsidian/Excel finomhangolas vagy konkret hasznalati visszajelzes alapjan induljon.
3. Parkolopalyan marad, nem elvetve: saved reasoning karakterhossz kijelzes, kulon reasoning copy gomb, stream kozbeni status text, delta throttling, code block copy/language badge/syntax highlighting, MarkdownContent wrapper, wrap/nowrap kapcsolo.
4. Nagyobb zaras elott ujra: `pytest -q`, `ruff check app tests`, `npm run build`.

## Tovabbra is halasztando

- attachments,
- RAG,
- folders/tags,
- user accounts,
- cloud sync,
- cross-chat memory,
- regenerate branching trees,
- prompt library.
