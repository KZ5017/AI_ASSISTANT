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
- regenerate latest assistant message,
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

Status: reszben kesz.

Jelenleg a fo UI nagyreszt `ChatShell.tsx`-ben van. Funkcionalisan mukodik, de kesobbi refaktorral erdemes lehet bontani:

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

Status: reszben kesz.

Megvan:

- backend pytest testek assistant persistence, health, LM provider, LM Studio API temakban,
- frontend `npm run build` tobbszor sikeresen futott.

A legutobbi UI modositasok utan ismert ellenorzes:

- `npm run build`: sikeres.

A teljes backend `pytest` + `ruff check app tests` futtatast erdemes ujra elvegezni nagyobb zaras elott.

## Kovetkezo logikus lepesek

1. Teljes backend ellenorzes: `pytest` es `ruff check app tests`.
2. Manual smoke Windows bongeszobol, LM Studioval.
   - A Windows start script legutobb sikeresen inditotta a `8000` backend es `5173` frontend listenereket; a felhasznalo visszajelzese alapjan mukodik.
3. UI komponensbontas, ha a `ChatShell.tsx` mar nehezen karbantarthato.
4. Finomabb hibauzenet/notice rendszer a modellpanelhez es composer warningokhoz.
5. Opcionlisan Playwright vagy mas frontend smoke teszt.

## Tovabbra is halasztando

- streaming,
- attachments,
- RAG,
- folders/tags,
- user accounts,
- cloud sync,
- cross-chat memory,
- regenerate branching trees,
- prompt library.
