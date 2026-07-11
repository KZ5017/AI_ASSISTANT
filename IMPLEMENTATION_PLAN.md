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

- Settings LM Studio base URL, chat model, timeout, context length, eval batch, flash attention, KV cache offload, auto-load, temperature, max output tokens.
- Native `/api/v1/models`, `/api/v1/models/load`, `/api/v1/models/unload`, `/api/v1/chat` hasznalat.
- Health/list/select/load/unload/chat backend endpointok.
- Runtime selected chat model state.
- Auto-load chat hivas elott, ha engedelyezett.
- Reasoning mapping: UI `normal` -> provider `off`, UI `model_default` -> provider `model_default`.

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

Status: kesz az aktualis frontend/docs zarashoz.

Megvan:

- backend pytest testek assistant persistence, health, LM provider, LM Studio API es streaming temakban,
- frontend `npm run build` sikeresen fut,
- ruff ellenorzes sikeres.

Legutobbi ismert ellenorzes:

- `pytest -q`: 32 passed, 1 ismert Starlette/httpx deprecation warning.
- `ruff check app tests`: passed.
- `npm run build`: passed.

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

## Kovetkezo logikus lepesek

1. Saved reasoning UI tovabbi finomhangolasa csak hasznalati visszajelzes alapjan. Az MVP kesz.
2. Opcionális saved reasoning karakterhossz kijelzes vagy kulon reasoning copy gomb, ha valodi igeny merul fel.
3. Opcionális status text stream kozben: modellbetoltes / prompt feldolgozas jelzese, ha a reasoning UI mellett hasznosnak tunik.
4. Opcionális delta throttling vagy frontend smoke teszt csak akkor, ha valodi teljesitmeny- vagy regresszio-kockazat latszik.
5. Nagyobb zaras elott ujra: `pytest -q`, `ruff check app tests`, `npm run build`.

## Tovabbra is halasztando

- attachments,
- RAG,
- folders/tags,
- user accounts,
- cloud sync,
- cross-chat memory,
- regenerate branching trees,
- prompt library.
