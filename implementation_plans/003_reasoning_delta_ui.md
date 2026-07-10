# 003 - Reasoning Delta UI Implementacios Terv

## Status

MVP implementacio kesz es felhasznaloi proban jonak itelve. A frontend futas kozben megjeleniti a reasoning_delta tartalmat egy atmeneti, preview/expanded modban mukodo Gondolatmenet panelben, DB persistence nelkul.

## Cel

A standalone AI Assistant mar kepes LM Studio streaming valaszokat kezelni, es az app-szintu SSE szerzodesben mar letezik a `reasoning_delta` event. A kovetkezo cel az, hogy a reasoning/gondolkodasi stream futas kozben lathato legyen egy visszafogott, opcionálisan lenyithato UI blokkban.

Ez a funkcio nem valtoztatja meg a projekt domain hatarait:

- nincs RAG,
- nincs dokumentum/source reference,
- nincs BoberDetective domain,
- nincs reasoning adatbazisba mentese,
- nincs utolagos tartos "gondolkodas megtekintese" funkcio.

## UX alapelv

A reasoning tartalom futas kozbeni, atmeneti betekintes. Nem fo valasz, nem bizonyitek, nem tartos chat history elem.

Felhasznaloi elv:

- akit erdekel, stream kozben meg tudja nezni,
- aki nem nyitja ki, annak csak egy finom "Gondolkodik" allapotjelzes latszik,
- a vegleges assistant valasz utan a reasoning UI eltunik,
- a chat historyban csak a vegleges assistant valasz marad.

## Iparagi minta es forrasok

A jelenlegi nagy nyelvi modellek feluletein es API-iban kirajzolodik egy kozos minta:

- a thinking/reasoning a vegleges valasztol elkulonitve jelenik meg,
- sokszor streamelheto,
- gyakran osszecsukhato vagy summary jellegu,
- a nyers vagy teljes belso gondolkodas nem feltetlenul tartos felhasznaloi tartalom.

Technikai forrasok:

- LM Studio native REST streaming: `reasoning.start`, `reasoning.delta`, `reasoning.end`, `message.delta`, `chat.end`.
  - https://lmstudio.ai/docs/developer/rest/streaming-events
- OpenAI reasoning modellek: reasoning tokenek es summary/encrypted reasoning szemlelet.
  - https://developers.openai.com/api/docs/guides/reasoning
  - https://openai.com/index/learning-to-reason-with-llms/
- Anthropic Claude extended thinking: thinking block, streaming `thinking_delta`, display `summarized` / `omitted`.
  - https://platform.claude.com/docs/en/build-with-claude/extended-thinking
- Gemini thinking: thought step, thought summary, streaming thought summary delta.
  - https://ai.google.dev/gemini-api/docs/thinking

## Javasolt UI

### Helye

A reasoning panel az aktualis pending assistant bubble resze legyen, a vegleges assistant valasz tartalma folott.

Indok:

- szemantikusan az adott assistant valaszhoz tartozik,
- nem keveredik a modellallapot panellel,
- nem general globalis UI zajt,
- normal send, regenerate es retry esetben ugyanazt a mintat tudja hasznalni.

### Alapallapot

Ha reasoning be van kapcsolva es erkezik legalabb egy `reasoning_delta`, megjelenik egy kicsi thinking blokk.

Feliratok:

- futas kozbeni allapot: `Gondolkodik`
- lenyithato blokk cime: `Gondolatmenet`

Alapbol legyen csukott, de stream kozben nyithato.

### Lenyitott allapot

Lenyitas utan a reasoning tartalom stream kozben epul:

- deltankent bovul,
- Markdown-kent renderelodik, de visszafogottabb stilussal, mint a vegleges assistant valasz,
- nem fo valasz es nem tartos history elem,
- kis betumerettel, visszafogott szinnel,
- max magassag utan belso fuggoleges scrollt kap.

Javasolt max magassag:

- desktop: 180-220px,
- mobil: 140-180px.

Vizszintes scroll ne jelenjen meg; a szoveg torjon.

### Animacio

A jelenlegi harompontos typing indicator helyett vagy mellett a thinking allapot kapjon finomabb, "thinking" jellegu animaciot.

Javaslat:

- kis `Lightbulb` vagy mas kontextushoz illo ikon,
- finom pulzalo narancs vagy tokenizalt primary accent,
- esetleg halk, balrol jobbra mozgo fenyvonal a `Gondolkodik` szoveg mellett.

Kerulendo:

- harsany spinner,
- nagy loader,
- tul eros arnyek vagy neon hatas,
- teljes panelt mozgató animacio.

## Eletciklus

### Normal send

1. User elkuldi az uzenetet.
2. Pending user message megjelenik.
3. Pending assistant message megjelenik.
4. Ha erkezik `reasoning_delta`, a pending assistant bubble tetejen megjelenik a thinking blokk.
5. Ha erkezik normal `delta`, a vegleges valasz tartalma a thinking blokk alatt streamelodik.
6. `done` utan a backend altal visszaadott vegleges chat detail kerul az UI-ba.
7. A reasoning panel eltunik, mert nincs DB-be mentve.

### Regenerate

Ugyanez a minta ervenyes:

- a regi assistant valasz helyen pending assistant valasz epul,
- ha van reasoning, ugyanott jelenik meg,
- sikeres `done` utan csak az uj vegleges assistant valasz marad,
- stop/hiba eseten a regi assistant valasz marad, reasoning panel eltunik.

### Retry last unanswered user

Ugyanez a minta ervenyes:

- az utolso megvalaszolatlan user uzenet alatt pending assistant bubble jelenik meg,
- reasoning panel a pending assistant bubble resze,
- sikeres `done` utan csak a vegleges assistant valasz marad,
- stop/hiba eseten user-only recovery allapot marad.

### Edit + Mentés és küldés

Ugyanazt a retry streaming flow-t hasznalja, tehat ugyanazt a reasoning UI-t kell kapnia.

## Stop, hiba es edge case-ek

### Stop/abort

- Stop/abort nem globalis hiba.
- Pending assistant bubble torlodhet vagy visszaallhat az eddigi recovery szabalyok szerint.
- Reasoning panel nem marad tartosan a chatben.

### Provider hiba

- Ha provider hiba tortenik, a reasoning panel eltunik a pending assistant bubble-lal egyutt.
- A globalis error/notice rendszer kezeli a hibat.
- Normal send es retry esetben user-only recovery allapot maradhat.
- Regenerate esetben a regi assistant valasz marad.

### Nincs reasoning delta

- Ha reasoning be van kapcsolva, de nem jon `reasoning_delta`, nem jelenik meg ures thinking panel.
- A meglevo typing/pending assistant allapot marad.
- Ez fontos, mert nem minden modell kuld reasoning tartalmat, es egyszeru promptokra egyes modellek nem gondolkodnak lathatoan.

### Reasoning delta erkezik, de nincs normal valasz

- Stream kozben a reasoning lathato lehet.
- Ha `done` nem ad vegleges assistant valaszt, a meglevo hiba-flow ervenyes.
- Reasoning tartalom ilyenkor sem mentodik.

## Adatkezeles

Elso implementacioban:

- reasoning tartalom csak frontend runtime state,
- nincs DB migration,
- nincs assistant message metadata mentese,
- nincs utolagos megtekintes,
- nincs contextbe visszakuldes.

Indok:

- lokalis UI feature-kent indul,
- kisebb kockazat,
- nem noveljuk a chat history zajat,
- nem kotjuk magunkat provider-specifikus reasoning formatumhoz.

Kesobbi opcionális irany:

- ha a user kifejezetten keri, lehet `assistant_message.metadata.reasoning_summary` vagy kulon ephemeral/debug storage,
- de ez most nem cel.

## Frontend implementacios terv

Erintett fajlok:

- `frontend/src/components/ChatShell.tsx`
- `frontend/src/components/MessageThread.tsx`
- `frontend/src/components/TypingIndicator.tsx` vagy uj `ReasoningPanel.tsx`
- `frontend/src/components/chatTypes.ts`
- `frontend/src/styles/app.css`
- `frontend/src/api/assistant.ts` csak akkor, ha a stream event tipuson pontositas kell.

### Javasolt komponens

Uj komponens:

```text
frontend/src/components/ReasoningPanel.tsx
```

Feladata:

- collapsed/expanded allapot renderelese,
- `Gondolkodik` status sor,
- `Gondolatmenet` lenyithato label,
- reasoning text megjelenitese,
- max magassag + belso scroll CSS osztalyok hasznalata.

### State modell

Javasolt pending assistant state kiegeszites:

```ts
type PendingAssistantState = {
  content: string;
  reasoningContent: string;
  isReasoningOpen: boolean;
};
```

Ha jelenleg egyszeru string pending assistant content van, akkor vagy:

1. minimalisan melle kerul egy `pendingReasoningContent` state, vagy
2. bevezetunk egy strukturalt pending assistant state-et.

Javaslat: a kisebb kockazat miatt elso korben kulon state-ek:

- `pendingAssistantContent`,
- `pendingReasoningContent`,
- `isReasoningOpen`.

Kesobb lehet osszefogni, ha a ChatShell ujabb bontasa indokolja.

### Stream event kezeles

Minden stream flow-ban azonosan:

- `start`: pending reasoning reset,
- `reasoning_delta`: append `content` a pending reasoning state-hez,
- elso reasoning delta utan a panel megjelenhet,
- `delta`: append a pending assistant contenthez,
- `done`: pending reasoning reset es chat detail sync,
- `error`: pending reasoning reset a jelenlegi hiba-flow szerint,
- abort: pending reasoning reset.

### Open/close allapot

Alap:

- panel csukva indul,
- user lenyithatja,
- a stream adott koren belul megmarad a valasztasa,
- kovetkezo send/regenerate/retry kezdetekor reset csukottra.

## CSS terv

Javasolt osztalyok:

```text
.reasoning-panel
.reasoning-panel__header
.reasoning-panel__status
.reasoning-panel__toggle
.reasoning-panel__body
.reasoning-panel__content
.reasoning-panel__pulse
```

Stilus:

- illeszkedjen a jelenlegi tokenizalt light/dark rendszerbe,
- ne legyen nagy kartya a kartyan belul,
- finom border vagy hatter eleg,
- radius a chat bubble-hoz igazodjon, de lehet kisebb,
- max-height + overflow-y auto,
- overflow-x hidden,
- `white-space: normal` a Markdown-renderelt reasoning tartalomnal,
- word-break/overflow-wrap vedje a hosszu sorokat,
- a preview/expanded magassag az eredeti kenyelmesebb ertekeken maradjon, a nagy ures sorokat ne CSS osszenyomassal, hanem reasoning-only whitespace normalizalassal kezeljuk.

## Backend terv

Backend oldalon elso korben valoszinuleg nincs uj endpoint vagy adatmodell.

Ellenorizni kell:

- a provider parser tenyleg tovabbitja-e a `reasoning.delta` tartalmat `reasoning_delta` app eventkent,
- a router SSE encoder minden stream flow-ban tovabbitja-e,
- a frontend API parser tipusa nem dobja-e el.

Ha ezek mar rendben vannak, backend kodvaltozas nem kell.

## Teszt es ellenorzes

Automata:

- `npm run build`,
- `pytest -q`,
- `ruff check app tests`.

Frontend manual smoke:

1. Reasoning toggle bekapcsolva.
2. Olyan modell/prompt hasznalata, amely kuld reasoning deltakat.
3. Stream kozben megjelenik `Gondolkodik`.
4. A `Gondolatmenet` lenyithato.
5. Lenyitva a reasoning tartalom stream kozben bovul.
6. Max magassag utan belso scroll jelenik meg, nincs vizszintes scroll.
7. Vegleges `done` utan a reasoning panel eltunik, csak a vegleges assistant valasz marad.
8. Stop eseten nincs globalis hiba, es reasoning panel nem marad a historyban.
9. Regenerate es retry flow-ban ugyanez mukodik.
10. Mobil nezetben a panel nem nyomja szet a layoutot.

## Kockazatok

- Egyes modellek nyers, hosszu vagy kaotikus reasoninget kuldhetnek; emiatt a panel ne legyen tul hangsulyos.
- Nem minden modell kuld reasoning deltakat; ures panel nem jelenhet meg.
- Ha tul nagy mennyisegu reasoning delta jon, render teljesitmeny gond lehet; ilyenkor kesobb delta throttling vagy chunkolt state update kellhet.
- A reasoning tartalom nem feltetlenul azonos a modell vegleges valaszaval; UI copy ne sugallja, hogy ez audit vagy bizonyitek.

## Kesz definicio

A feature akkor tekintheto kesznek, ha:

- reasoning delta stream kozben lathato, de opcionális,
- alapbol csak finom `Gondolkodik` allapot jelenik meg,
- a `Gondolatmenet` lenyithato,
- a panel max magassaggal es belso scrollal mukodik,
- done utan nem marad reasoning tartalom a chat historyban,
- normal send, regenerate, retry es edit+send flow-ban egységesen mukodik,
- nincs DB migration es nincs reasoning persistence,
- Markdown render es whitespace normalizalas mukodik,
- build/test zold.

## Megvalosult implementacios lepesek

1. Frontend pending assistant state kiegeszult reasoning contenttel es lenyitasi allapottal.
2. Letrejott a `ReasoningPanel.tsx` komponens.
3. A `MessageThread.tsx` pending assistant renderje megjeleniti a reasoning panelt.
4. A streaming handlerek kezelik az `onReasoningDelta` eventet normal send, regenerate, retry es edit+send flow-ban.
5. A CSS light/dark tokenekhez igazodo preview/expanded panelt ad.
6. A reasoning panel Markdown renderelest es whitespace normalizalast kapott.
7. `npm run build`, `pytest -q` es `ruff check app tests` zold volt a zaro korokben.

## Preview/expanded finomitas

A reasoning panel MVP utan a mukodes pontosodott:

- ha erkezik reasoning tartalom, a panel nem marad teljesen csukva,
- automatikusan megjelenit egy par soros preview body-t,
- a nyil ikon ilyenkor tovabbra is a nem teljesen kinyitott allapotot jelzi,
- a preview max magassag utan belso scrollt kap,
- uj delta erkezesekor a panel automatikusan az aljara gorget, igy mindig a legfrissebb sorok latszanak,
- user kattintasra a preview expanded allapotba valt, nagyobb, de tovabbra is limitált magassaggal,
- expanded allapotban is megmarad az automatikus aljara gorgetes es a belso scroll.

## Reasoning whitespace normalizalas

A reasoning modellek gyakran sok egymas utani ures sort vagy minden logikai sor koze dupla sortorest streamelnek. A vegleges assistant valaszhoz nem nyulunk, de a Gondolatmenet panelben a megjelenites elott normalizalunk:

- CRLF sortores LF-re valt,
- sorvegi whitespace torlodik,
- whitespace-only sorok tisztulnak,
- ketto vagy tobb egymast koveto sortores egyetlen sortoresre tomorul,
- eleji ures sorok torlodnek.

Ez csak a reasoning panel display tartalmat erinti; a runtime stream content state nem modosul.
