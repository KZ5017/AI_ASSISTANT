# 001 - LM Studio Streaming Assistant Valaszok Implementacios Terv

## Cel

A standalone AI Assistant jelenleg csak akkor jeleniti meg az assistant valaszt, amikor az LM Studio teljes valasza mar visszaerkezett. A cel az, hogy az assistant valasza folyamatosan, streaming modban epuljon a chatben, hasonloan a megszokott modern chat UI-khoz.

A terv nem valtoztat a projekt domain hatarain:

- nincs RAG,
- nincs document/source reference,
- nincs BoberDetective domain,
- nincs Qdrant/embedding/OCR/Docling,
- a streaming csak altalanos chat valasz-megjelenites.

## Valasztott technikai irany

A projekt jelenlegi backendje mar az LM Studio natív REST API-jat hasznalja:

```text
POST /api/v1/chat
```

Ezert a streaminghez is ezt kell megtartani, es a request payloadba bekerul:

```json
{
  "stream": true
}
```

Az LM Studio ilyenkor Server-Sent Events (SSE) formatumu event streamet kuld vissza.

A backend a streamet nem engedi kozvetlenul nyersen a frontendhez, hanem stabil, sajat app-szintu SSE esemeny szerzodest ad:

```text
LM Studio SSE -> backend normalizalas -> app SSE -> frontend fetch stream parser
```

Indok:

- a frontend ne fuggjon kozvetlenul az LM Studio belso event formatumatol,
- kesobb mas provider is bekotheto ugyanabba a frontend szerzodesbe,
- a backend tudja kontrollalni a DB mentest, hibat, done eventet.

## Hivatalos informacios alap

LM Studio dokumentacio alapjan:

- `POST /api/v1/chat` tamogatja a `stream: true` opciot.
- A stream SSE formatumu.
- Fontos eventek:
  - `chat.start`,
  - `model_load.start`,
  - `model_load.progress`,
  - `model_load.end`,
  - `prompt_processing.start`,
  - `prompt_processing.progress`,
  - `prompt_processing.end`,
  - `reasoning.start`,
  - `reasoning.delta`,
  - `reasoning.end`,
  - `message.start`,
  - `message.delta`,
  - `message.end`,
  - `error`,
  - `chat.end`.
- A `chat.end` tartalmazza a vegleges aggregalt eredmenyt, ami megfelel a non-streaming valasznak.

Forrasok:

- https://lmstudio.ai/docs/developer/rest
- https://lmstudio.ai/docs/developer/rest/chat
- https://lmstudio.ai/docs/developer/rest/streaming-events
- https://lmstudio.ai/docs/developer/openai-compat/chat-completions
- https://lmstudio.ai/docs/developer/openai-compat/responses
- https://fastapi.tiangolo.com/advanced/custom-response/

## Jelenlegi kodhelyzet

Erintett fajlok:

```text
backend/app/llm_provider.py
backend/app/assistant_service.py
backend/app/routers/assistant.py
backend/app/schemas.py
frontend/src/api/assistant.ts
frontend/src/components/ChatShell.tsx
frontend/src/styles/app.css
backend/tests/
```

Jelenlegi non-streaming flow:

```text
Frontend POST /assistant/chats/{id}/messages
Backend menti user message-et
Backend meghivja provider.chat_completion(...)
LM Studio teljes valaszt ad
Backend menti assistant message-et
Backend visszaadja a teljes chat detailt
Frontend ujrarendereli a chatet
```

Tervezett streaming flow:

```text
Frontend POST /assistant/chats/{id}/messages/stream
Backend menti user message-et
Backend elinditja LM Studio streamet
Backend delta eventeket kuld frontendnek
Frontend epiti az ideiglenes assistant bubble-t
LM Studio chat.end erkezik
Backend menti a vegleges assistant message-et
Backend done eventben visszaadja a friss chat detailt
Frontend szinkronizal a vegleges chat allapotra
```

## Backend app-szintu SSE szerzodes

A frontend fele kuldott event formatum legyen egyszeru es stabil.

### `start`

A stream elindult, a user message mar mentve van.

```text
event: start
data: {"chat_id": 1}
```

Opcionalis jovobeli mezok:

```json
{
  "chat_id": 1,
  "user_message_id": 10
}
```

### `delta`

Assistant valasz darab.

```text
event: delta
data: {"content": "Szia"}
```

### `reasoning_delta`

Reasoning/gondolkodas darab. Elso implementacioban megjelenithetjuk minimalisan vagy csak gyujthetjuk.

```text
event: reasoning_delta
data: {"content": "Vegiggondolom"}
```

### `status`

Opcionális status/progress informacio LM Studio eventekbol.

```text
event: status
data: {"phase": "prompt_processing", "progress": 0.5}
```

Elso MVP-ben ez kihagyhato, de a backend parser tudhatja.

### `error`

Stream kozbeni hiba.

```text
event: error
data: {"message": "LM Studio hiba"}
```

### `done`

A backend befejezte a streamet, a vegleges assistant message DB-be mentve, a chat detail visszakuldheto.

```text
event: done
data: {"chat": {...}}
```

A `done.chat` ugyanazt a formatumot hasznalja, mint a jelenlegi `AssistantChatDetailResponse`.

## Backend provider terv

Fajl: `backend/app/llm_provider.py`

### Uj dataclassok

```python
@dataclass(frozen=True)
class LLMStreamEvent:
    type: str
    content: str | None = None
    error_message: str | None = None
    final_content: str | None = None
    model: str | None = None
    raw: dict[str, Any] | None = None
```

A `type` ajanlott ertekei:

```text
start
message_delta
reasoning_delta
status
error
done
```

### Uj provider metodus

```python
def chat_completion_stream(
    self,
    model: str,
    messages: list[LLMChatMessage],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_mode: str | None = "off",
) -> Iterator[LLMStreamEvent]:
    ...
```

### Payload epites

A payload ugyanaz legyen, mint a jelenlegi `chat_completion()` metodusban, csak ezzel kiegeszitve:

```python
payload["stream"] = True
```

Tovabbra is tartani kell:

- `model`,
- `input`,
- `system_prompt`,
- `temperature`,
- `store: False`,
- `max_output_tokens`, ha van,
- `reasoning: off`, ha a UI reasoning kikapcsolt es a modell tamogatja.

### HTTP stream

`httpx.Client.stream()` hasznalata:

```python
with client.stream("POST", "/api/v1/chat", json=payload) as response:
    response.raise_for_status()
    for line in response.iter_lines():
        ...
```

Megjegyzes: ha a provider most sync `httpx.Client`-et hasznal, elso korben maradhat sync generator. FastAPI `StreamingResponse` tud normal generatorbol is streamelni.

### SSE parser

Minimalis parser feladata:

- gyujti az `event:` sort,
- gyujti a `data:` sort vagy sorokat,
- ures sor eseten lezart SSE frame,
- JSON parse a data-ra,
- ismert LM Studio eventek normalizalasa.

LM Studio -> provider mapping:

```text
message.delta      -> LLMStreamEvent(type="message_delta", content=...)
reasoning.delta    -> LLMStreamEvent(type="reasoning_delta", content=...)
error              -> LLMStreamEvent(type="error", error_message=...)
chat.end           -> LLMStreamEvent(type="done", final_content=..., model=..., raw=...)
model_load.*       -> LLMStreamEvent(type="status", raw=...)
prompt_processing.*-> LLMStreamEvent(type="status", raw=...)
```

### Vegleges content kinyerese `chat.end`-bol

LM Studio `chat.end` eventben a `result.output` lista tartalmazhat tobb itemet. A vegleges assistant contentet ugyanugy kell kinyerni, mint a non-streaming metodusban:

```python
content_parts = [
    item["content"]
    for item in output
    if item.get("type") == "message"
]
final_content = "\n".join(content_parts)
```

Ha nincs message content, provider hibat kell generalni.

## Assistant service terv

Fajl: `backend/app/assistant_service.py`

### Normal kuldes streaminggel

Uj fuggveny:

```python
def send_message_stream(
    db: Session,
    chat_id: int,
    content: str,
    *,
    reasoning_mode: str | None = None,
    temperature: float | None = None,
    settings: Settings | None = None,
    provider: LMStudioNativeProvider | None = None,
) -> Iterator[AssistantStreamEvent]:
    ...
```

Vagy egyszerubb: a router generatora hivja a service elokeszito es finalize helperjeit. Ket jo opcio van.

### Ajanlott service bontas

A legkevesbe kockazatos bontas:

```python
def prepare_send_message(...):
    # validal, user message-et ment, visszaadja chat + llm_messages + metadata


def finalize_assistant_message(...):
    # chat_id, sequence_index, content, model, reasoning -> DB mentés
```

Ez jobban tesztelheto, mint egy nagy generator.

### Sorrend

1. Active chat betoltese.
2. User content `strip()` es ures validacio.
3. Effective reasoning/temperature meghatarozasa.
4. `next_sequence` kiszamitasa.
5. Context budget ellenorzes a pending user message-dzsel.
6. User message letrehozasa.
7. Elso user message es default title eseten title frissites.
8. Chat reasoning/temperature/updated_at frissites.
9. DB commit.
10. LLM stream inditas.
11. Deltak tovabbadasa.
12. `done` eseten assistant message mentese `next_sequence + 1` indexszel.
13. Friss chat detail visszatoltese.

### DB irasi szabaly

- User message: stream indulasa elott mentve.
- Assistant message: csak vegleges `chat.end` utan mentve.
- Tokenenkent/deltankent nincs DB iras.

Indok:

- stabilabb,
- gyorsabb,
- kisebb DB terheles,
- nincs sok felkesz allapot.

### Stream megszakadas

Ha a frontend megszakitja a kapcsolatot:

- user message mar mentve marad,
- assistant message nem mentodik,
- UI ujratolteskor latszani fog a user message assistant valasz nelkul.

Ez elfogadhato MVP viselkedes. Késobb lehet `interrupted` assistant metaallapotot bevezetni, de elso korben ne legyen migration.

## Regenerate streaming terv

Masodik fazisban javasolt.

Endpoint:

```text
POST /api/assistant/chats/{chat_id}/regenerate/stream
```

Sorrend:

1. Active chat betoltese.
2. Ellenorzes: van legalabb 2 message.
3. Utolso message assistant, elotte user.
4. Context = chat.messages[:-1].
5. Context budget ellenorzes.
6. Regi assistant torlese.
7. DB commit vagy flush.
8. LLM stream inditas.
9. Deltak frontendnek.
10. `chat.end` utan uj assistant message mentese a regi sequence indexre.
11. Done event friss chat detaillel.

Elso implementacioban a regenerate maradhat non-streaming, hogy a normal send streaming stabilan elkészüljön.

## Router terv

Fajl: `backend/app/routers/assistant.py`

### Uj endpoint normal kuldeshez

```python
@router.post('/chats/{chat_id}/messages/stream')
def send_assistant_message_stream(...):
    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
```

### SSE encoding helper

Backend helper:

```python
def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
```

### Exception mapping

Stream elotti hibak maradhatnak normal HTTP hibak:

- chat not found,
- validation error,
- context limit,
- provider nem elerheto stream inditas elott.

Stream kozbeni hibak menjenek SSE `error` eventkent:

```text
event: error
data: {"message": "..."}
```

Majd a generator zarjon.

## Frontend API terv

Fajl: `frontend/src/api/assistant.ts`

### Uj type-ok

```ts
export type AssistantStreamEvent =
  | { event: 'start'; data: { chat_id: number } }
  | { event: 'delta'; data: { content: string } }
  | { event: 'reasoning_delta'; data: { content: string } }
  | { event: 'status'; data: { phase?: string; progress?: number } }
  | { event: 'error'; data: { message: string } }
  | { event: 'done'; data: { chat: AssistantChatDetail } };
```

### Uj fuggveny

```ts
export async function streamAssistantMessage(
  chatId: number,
  payload: { content: string; reasoning_mode?: AssistantReasoningMode | null },
  handlers: {
    onStart?: () => void;
    onDelta: (content: string) => void;
    onReasoningDelta?: (content: string) => void;
    onStatus?: (status: unknown) => void;
    onDone: (chat: AssistantChatDetail) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void>
```

### `fetch` streaming parser

Nem `EventSource`, mert az GET-alapu, nekunk POST body kell.

Hasznalando:

```ts
const response = await fetch(url, { method: 'POST', body, signal });
const reader = response.body?.getReader();
const decoder = new TextDecoder();
```

Parser logika:

- chunk decode `stream: true` opcioval,
- bufferbe append,
- `\n\n` szerint frame-ekre bontas,
- frame-bol `event:` es `data:` sorok kinyerese,
- JSON parse,
- handler hivas.

### HTTP error kezeles

Ha `response.ok === false`, akkor ugyanugy olvassuk JSON-kent, mint a mostani `readJsonResponse`.

Ha nincs `response.body`, hiba:

```text
A bongeszo nem tamogatja a streaming valasz olvasasat.
```

## ChatShell terv

Fajl: `frontend/src/components/ChatShell.tsx`

### Jelenlegi kuldesi flow csereje

Most:

```ts
const updatedChat = await sendAssistantMessage(...)
setActiveChat(updatedChat)
```

Uj:

```ts
setPendingUserMessage(...)
setPendingAssistantContent('')
await streamAssistantMessage(..., {
  onDelta: append,
  onDone: setActiveChat,
  onError: setWarning,
})
```

### Ajanlott UI state-ek

```ts
const [pendingAssistantContent, setPendingAssistantContent] = useState('');
const [pendingReasoningContent, setPendingReasoningContent] = useState('');
const [streamAbortController, setStreamAbortController] = useState<AbortController | null>(null);
```

Mar letezo pending user message mechanika felhasznalhato, ha van.

### Render

A message thread vegen:

- pending user message,
- pending assistant bubble, ha `pendingAssistantContent` vagy stream fut,
- pending typing indicator helyett/ mellett a streaming bubble.

### Done utan

`onDone(chat)`:

- `setActiveChat(chat)`,
- `setPendingUserMessage(null)`,
- `setPendingAssistantContent('')`,
- `setPendingReasoningContent('')`,
- `setIsSending(false)`.

A teljes chat detail ujraszinkronizalas fontos, mert igy a DB es UI biztosan egyezik.

## Reasoning UI terv

Elso implementacioban minimalis:

- ha `pendingReasoningContent` nem ures, megjelenhet egy kicsi, visszafogott blokk az assistant pending bubble folott:

```text
Gondolkodas...
<reasoning text>
```

De elso korben az is elfogadhato, hogy csak gyujtjuk es nem rendereljuk. Mivel a jelenlegi appban nincs kulon reasoning persistence, ne nyissunk adatbazis migrationt csak emiatt.

Javaslat:

- Phase 1: reasoning delta gyujtese, UI-ban optional collapsed/hidden.
- Phase 2: esztetikus reasoning panel, ha a user keri.

## Cancel / abort terv

Elso MVP-ben eleg:

- stream kozben composer disabled,
- uj uzenet nem kuldheto,
- route/chat valtasnal `AbortController.abort()`.

Kovetkezo iteracio:

- kulon `Megallitas` gomb,
- megszakitott assistant valasz opcionális mentese vagy eldobasa.

MVP dontes:

- megszakitott assistant valaszt ne mentsunk DB-be,
- user message maradjon meg.

## Markdown streaming viselkedes

A partial assistant contentet a jelenlegi Markdown renderer renderelheti.

Varhato jelenseg:

- felig nyitott markdown syntax neha atmenetileg furcsan renderel.

Ez elfogadhato. Ha tul sok render tortenik, kesobb throttle:

```text
UI update max 30-60 ms-onkent
```

Első korben nem kell throttling, csak ha teljesitmeny problema latszik.

## Tesztterv

### Backend unit tesztek

1. SSE parser egy `message.delta` frame-et helyesen olvas.
2. SSE parser tobb frame-et helyesen olvas.
3. `reasoning.delta` normalizalodik.
4. `error` event normalizalodik.
5. `chat.end` eventbol final message content kinyerheto.
6. Hianyzo final message content provider hibahoz vezet.

### Assistant service tesztek

1. Streaming send elott user message mentodik.
2. Streaming done utan assistant message mentodik.
3. Delta kozben nincs assistant DB iras.
4. Error eseten assistant message nem mentodik.
5. Context limit stream endpointnal is ervenyesul.

### Router tesztek

1. `/messages/stream` `text/event-stream` valaszt ad.
2. Sikeres stream tartalmaz `start`, `delta`, `done` eventet.
3. Validation hiba stream elott normal HTTP 400.
4. Provider hiba stream kozben `error` event.

### Frontend tesztek

1. SSE parser `delta` eventet handlerbe ad.
2. SSE parser `done` eventet chat objektummal ad.
3. Partial chunk split eseten is mukodik.
4. `npm run build` kotelezo.

### Manual smoke

1. Start script futtatasa Windowsbol.
2. LM Studio modell betoltve.
3. Uj chat.
4. Hosszabb prompt, amely lathatoan streamel.
5. Enter kuldes mukodik.
6. Shift+Enter sortores mukodik.
7. Done utan refresh utan is latszik a vegleges assistant message.
8. Regenerate elso korben meg mukodik non-streaming modban.

## Bevezetesi fazisok

### Phase A - Backend provider streaming alap

Status: kesz.

Megvalosult:

- SSE parser helper.
- `LLMStreamEvent` tipus.
- `chat_completion_stream()` provider metodus.
- Kozos payload epito a non-streaming es streaming chat hivasokhoz.
- Provider unit tesztek `message.delta`, `reasoning.delta`, `error`, `chat.end` es payload szabalyokra.

Ellenorzes:

- `pytest tests/test_lm_provider.py -q`: 9 passed.
- `ruff check app tests`: passed.
- `pytest -q`: 19 passed, 1 ismert Starlette/httpx deprecation warning.

### Phase B - Assistant send streaming endpoint

Status: kesz.

Megvalosult:

- `prepare_send_message_stream()` service helper: validacio, context guard, user message mentese, LLM payload elokeszites.
- `finalize_streamed_assistant_message()` service helper: vegleges assistant valasz mentese `chat.end` utan.
- `POST /api/assistant/chats/{chat_id}/messages/stream` endpoint `text/event-stream` valasszal.
- App-szintu SSE event formatum: `start`, `delta`, `reasoning_delta`, `status`, `error`, `done`.
- Stream kozbeni provider hiba SSE `error` eventkent jon vissza, assistant message mentese nelkul.
- `done` esemenyben friss chat detail payload erkezik, es DB-ben csak a vegleges assistant valasz tarolodik.

Ellenorzes:

- `pytest tests/test_assistant_persistence.py -q`: 9 passed, 1 ismert Starlette/httpx deprecation warning.
- `pytest tests/test_lm_provider.py -q`: 9 passed.
- `ruff check app tests`: passed.
- `pytest -q`: 21 passed, 1 ismert Starlette/httpx deprecation warning.

Kovetkezo logikus lepes:

- Phase C: frontend `streamAssistantMessage()` API helper es SSE parser, majd a normal kuldesi flow atallitasa streamingre.

### Phase C - Frontend normal send streaming

Status: kesz.

Megvalosult:

- `streamAssistantMessage()` frontend API helper `fetch()` + `ReadableStream` alapon.
- Frontend SSE parser `start`, `delta`, `reasoning_delta`, `status`, `error`, `done` esemenyekhez.
- `ChatShell.tsx` normal kuldesi flow streamingre allitva.
- Kuldes kozben ideiglenes user es assistant message jelenik meg.
- Az assistant pending message tartalma `delta` esemenyenkent bovul.
- Ures pending assistant tartalomnal a meglevo `TypingIndicator` jelenik meg.
- `done` utan a backend altal visszaadott friss chat detail kerul az UI-ba.
- Stream kozbeni provider hiba eseten az assistant pending message nem marad bent, es a chat frissul a mar mentett user message-dzsel.
- Regenerate egyelore szandekosan non-streaming maradt.

Ellenorzes:

- `npm run build`: passed.
- `ruff check app tests`: passed.
- `pytest -q`: 21 passed, 1 ismert Starlette/httpx deprecation warning.

Kovetkezo logikus lepes:

- Phase D: regenerate streaming endpoint es frontend flow, hogy az utolso assistant valasz ujrageneralasa is tokenenkent jelenjen meg.

### Phase D - Regenerate streaming

Status: kesz.

Megvalosult:

- Backend `prepare_regenerate_message_stream()` service helper.
- Backend `POST /api/assistant/chats/{chat_id}/regenerate/stream` endpoint.
- Regenerate stream ugyanazt az app-szintu SSE szerzodest hasznalja, mint a normal send: `start`, `delta`, `reasoning_delta`, `status`, `error`, `done`.
- Regenerate stream esetben a regi utolso assistant valasz csak sikeres `chat.end` utan cserelodik; stop/hiba eseten a regi assistant valasz megmarad.
- Stream kozbeni provider hiba eseten nem marad felkesz assistant rekord; normal send esetben a chat a user message-ig frissul vissza, regenerate esetben a regi assistant valasz megmarad.
- Frontend `streamRegenerateAssistantMessage()` API helper.
- `ChatShell.tsx` regenerate flow streamingre allitva: a regi assistant valasz helyen pending assistant valasz epul deltaonkent.

Ellenorzes:

- `pytest tests/test_assistant_persistence.py -q`: 11 passed, 1 ismert Starlette/httpx deprecation warning.
- `ruff check app tests`: passed.
- `npm run build`: passed.
- `pytest -q`: 23 passed, 1 ismert Starlette/httpx deprecation warning.

### Phase E - UX polish

Status: aktualis MVP kesz.

Megvalosult:

- Desktopon is lathato `Küldés` gomb, Enter kuldes megtartasaval.
- Stream kozben a composer gomb `Leállítás` allapotba tud valtani frontend aborttal.
- Regenerate stop/hiba eseten a regi assistant valasz megorzese a celzott szabaly.

Meg nyitott, kulon feature-korben kezelendo polish:

- Reasoning delta megjelenites. A backend es frontend SSE parser mar ismeri a `reasoning_delta` esemenyt, de a UI jelenleg nem rendereli kulon.
- Optional status text: modell betoltes / prompt feldolgozas.
- Optional delta throttling, ha a reasoning/status megjelenitesnel valodi teljesitmenyigeny merul fel.

### Phase F - Megvalaszolatlan utolso user uzenet recovery

Cel:

- Normal send stream leallitasa vagy hibaja utan eloallhat olyan chat allapot, ahol az utolso uzenet `user`, es nincs utana `assistant` valasz.
- Ezt nem toroljuk automatikusan, mert a user lehet, hogy meg akarja tartani az uzenetet.
- Viszont ne legyen esztetikailag es kontextus szempontbol zsakutca: az utolso megvalaszolatlan user uzenethez legyen explicit javitasi workflow.

#### Phase F1 - Detektalas es ujrakuldes

Backend terv:

- Uj service helper: `prepare_retry_last_user_message_stream(db, chat_id, ...)`.
- Ellenorzesek:
  - aktiv chat letezik,
  - van legalabb egy message,
  - az utolso message role-ja `user`,
  - nincs utana assistant valasz, mert ez csak az utolso message-re ertelmezett,
  - context budget rendben.
- A helper nem hoz letre uj user message-et es nem duplikal inputot.
- LLM context: a teljes jelenlegi chat message lista, amely user uzenettel zarul.
- Assistant sequence index: `last_user.sequence_index + 1`.
- Uj endpoint: `POST /api/assistant/chats/{chat_id}/retry-last-user/stream`.
- Ugyanazt az app-szintu SSE szerzodest hasznalja, mint a send/regenerate stream: `start`, `delta`, `reasoning_delta`, `status`, `error`, `done`.
- `done` utan a backend menti az assistant valaszt.
- Stop/hiba eseten nem ment felkesz assistant valaszt; a megvalaszolatlan user uzenet megmarad.

Frontend terv:

- Detektalas: `activeChat.messages.at(-1)?.role === "user"`.
- Csak az utolso user buborek alatt jelenjen meg recovery action row.
- Gombok elso korben:
  - `Újraküldés`: streameli az assistant valaszt a legutolso user uzenetre.
  - `Szerkesztés`: Phase F2-ben lesz aktiv; F1-ben hidden legyen, hogy ne igerjen kesz funkciot.
- `Újraküldés` kozben pending assistant buborek jelenik meg az utolso user uzenet alatt.
- A composer `Leállítás` gombja ugyanugy abortalja ezt a streamet is.

Teszt terv:

- Backend sikeres retry: user-only chat vegere assistant valasz mentodik.
- Backend invalid retry: ha utolso message assistant, 400 validacios hiba.
- Backend provider error: user-only allapot megmarad, nincs assistant mentve.
- Frontend build kotelezo.

Kesz definicio:

- Stopolt normal send utan az utolso user uzenet alatt latszik az `Újraküldés` action.
- Ujrakuldes nem duplikalja a user uzenetet.
- Ujrakuldes streaminggel epiti fel az assistant valaszt.

#### Phase F2 - Inline szerkesztes es mentes + kuldes

Backend terv:

- Uj service helper: `update_unanswered_last_user_message(db, chat_id, message_id, content)`.
- Uj endpoint javaslat: `PATCH /api/assistant/chats/{chat_id}/messages/{message_id}`.
- Guardok:
  - csak aktiv chat,
  - csak az utolso message szerkesztheto,
  - csak akkor, ha az utolso message role-ja `user`,
  - uresre trimelt content tilos,
  - context budget ujraszamolando,
  - answered user message nem szerkesztheto.
- A szerkesztes utan ket lehetoseg:
  - csak mentes,
  - vagy `Mentés és küldés`, amely update utan ugyanazt a retry stream flow-t inditja.
- Javaslat MVP-re: UI-ban `Mentés és küldés` legyen az elsodleges flow, mert ez az allapot eleve valasz nelkuli.

Frontend terv:

- Az utolso megvalaszolatlan user bubble inline szerkesztheto allapotba valthat.
- Bubble helyen textarea jelenik meg az aktualis user tartalommal.
- Akciok:
  - `Mentés és küldés`,
  - `Mégse`.
- Enter viselkedes:
  - szerkeszto textarea-ban Shift+Enter sortores,
  - kuldes csak explicit gombbal tortenjen, hogy ne legyen veletlen elkuldes.
- Mentes utan pending assistant stream indul ugyanugy, mint retry esetben.

Teszt terv:

- Backend successful edit updates last unanswered user content.
- Backend edit rejected when message is not last.
- Backend edit rejected when latest message is assistant.
- Backend edit rejected on empty content/context overflow.
- Frontend build kotelezo.

Kesz definicio:

- Stopolt user uzenet inline javithato.
- `Mentés és küldés` utan nem duplikalodik user message, a modositott textre jon assistant valasz.

#### Phase F3 - Recovery UX polish es dokumentacio

Status: kesz az aktualis recovery zarashoz.

Feladatok:

- Recovery action row ikonok es stilus veglegesitese kesz.
  - `Szerkesztés`: `Pencil` ikon.
  - `Újraküldés`: `Send` ikon.
  - `Mentés és küldés`: `Send` ikon.
  - `Mégse`: `X` ikon.
- Composer warning/hiba szovegek recovery esetekre nem kaptak kulon uj copy-t; a jelenlegi hiba/warning slot stabil maradt.
- Stop utan nem jelenik meg hibakent az abort; a UI csendesen marad recovery allapotban.
- Recovery editor textarea autosize: lefele no, nincs manual resize, es csak fuggoleges scrollbar jelenhet meg.
- Allapotfajlok frissitese.
- Manual smoke:
  1. normal send indit,
  2. leallitas,
  3. user-only recovery action megjelenik,
  4. ujrakuldes streaminggel valaszol,
  5. uj stop utan user-only allapot megmarad,
  6. szerkesztes + `Mentés és küldés` mukodik.

Kesz definicio:

- A megvalaszolatlan utolso user uzenet kontrollalt, esztetikus allapot.
- Nincs automatikus torles.
- Nincs user uzenet duplikacio.
- A kovetkezo normal kuldes elott a user erthetoen latja, hogy az elozo kor valasz nelkul maradt.

## Fontos implementacios dontesek

1. DB-be csak vegleges assistant valasz keruljon.
2. Stop/abort nem hiba UX szempontbol; recovery allapotot hozhat letre.
3. Regenerate stop/hiba eseten a regi assistant valasz maradjon meg.
4. Normal send stop/hiba eseten a user uzenet maradjon meg, es Phase F recovery kezelje.
5. Reasoning content elso korben ne kapjon DB migrationt.
6. Frontend `fetch` streaming legyen, ne `EventSource`.
7. Backend sajat SSE szerzodest adjon, ne LM Studio eventeket engedje at nyersen.
8. A meglévő non-streaming endpointok maradjanak meg fallbacknek legalabb az elso iteracioban.

## Visszagorgetesi terv

Ha streaming implementacio instabil:

- frontendben vissza lehet kapcsolni a regi `sendAssistantMessage()` hivasra,
- backend non-streaming endpointok valtozatlanul megmaradnak,
- provider `chat_completion()` marad a biztos fallback,
- adatmodell nem valtozik, ha nem mentunk reasoning contentet kulon.

Ezert az elso streaming MVP nem igenyel adatbazis migrationt.

## Lezart UX dontesek

1. Recovery edit textarea Enter viselkedese explicit gombos: kuldes csak `Mentés és küldés` gombbal.
2. Recovery `Szerkesztés` F2-ben bekerult, F1-ben nem igerte a UI.
3. Stop/abort nem globalis hiba, hanem recovery allapotot hagyhat maga utan.
4. Reasoning delta UI megjelenites a kovetkezo tudatos feature-irany, a mar meglevo `reasoning_delta` SSE szerzodesre epitve.

## Aktualis zaras es kovetkezo kodolasi lepes

F1, F2 es F3 kesz: az utolso megvalaszolatlan user uzenet ujrakuldheto, inline szerkesztheto, autosize editorral javithato, es `Mentés és küldés` utan duplikacio nelkul streamelt assistant valaszt kap.

A streaming/recovery/error-notice MVP utan a kovetkezo logikus irany: reasoning delta UI megjelenites. Ennek alapja mar adott:

- backend app-szintu SSE szerzodesben van `reasoning_delta`,
- frontend stream parser kezeli az eventet,
- a UI-ban kell donteni es implementalni, hol es hogyan jelenjen meg a gondolkodasi tartalom,
- elso korben adatbazis migration nelkul is megoldhato, ha a reasoning csak live, ideiglenes stream tartalomkent jelenik meg.
