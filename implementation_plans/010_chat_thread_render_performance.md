# 010 - Chat Thread Render Performance Plan

## Cel

Ez a terv a hosszabb chatfolyamok melletti UI reszponzivitast rogziti es tervezi.

A konkret tunet: hosszabb, Markdownban gazdag beszelgetesnel a composerbe torteno gepeles neha darabosnak tunhet. A chatfolyam tartalma ilyenkor nem valtozik, megis elofordulhat, hogy a React ujrarendereli a teljes message threadet es a benne levo draga Markdown tartalmakat.

Cel:

- a composer input maradjon folyamatos es gyors hosszabb chat history mellett is,
- a korabbi uzenetek ne renderelodjenek ujra feleslegesen minden karakterleuteskor,
- a scroll-follow es reasoning viselkedes ne romoljon,
- a megoldas fokozatos, kis kockazatu lepesekbol alljon.

## Kiindulasi pont

A jelenlegi frontend architektura:

- `ChatShell.tsx` tartja a legtobb workflow state-et,
- `input` state minden karakterleuteskor valtozik,
- `MessageThread.tsx` rendereli az osszes lathato uzenetet,
- assistant valaszok `ReactMarkdown` + `remark-gfm` renderelest hasznalnak,
- saved reasoning es live reasoning panelek szinten Markdown jellegu tartalmat renderelhetnek,
- a composer textarea es a recovery editor textarea autosize logikat hasznal,
- a message thread scroll-follow es ResizeObserver alapu logikakat hasznal.

A teljesitmeny szempontbol draga reszek:

- hosszu assistant Markdown valaszok ujrarenderelese,
- tablazatok, listak, code blockok es linkek ujraepitese,
- saved reasoning disclosure-ok ujrarenderelese,
- `activeMessages` es context karakter szamitas ismelt lefutasa,
- layout meresek autosize textarea es scroll-follow miatt.

## Aktualis kapcsolodo javitas

Status: kisebb UI/scroll reszponzivitas javitas megvalositva.

Megvaltozott:

- az inline recovery user editor alul tartja a message threadet, ha a user eleve a chatfolyam aljan volt,
- a textarea autosize hook `useLayoutEffect`-et hasznal, hogy paste vagy tobb soros novekedes eseten a meretezes a vizualis kirajzolas elott tortenjen,
- a megoldas nem rangatja vissza a usert az aljara, ha korabban felgorgetett.

Erintett fajlok:

- `frontend/src/components/ChatShell.tsx`,
- `frontend/src/hooks/useAutosizeTextarea.ts`.

Ez a javitas nem oldja meg a hosszu chatfolyam melletti altalanos render performance kerdest, de ugyanabba a UI-reszponzivitas temakorbe tartozik.

## Hatarok

Elso korben cel:

- felesleges rerenderek csokkentese,
- memoizacio es komponensbontas kis kockazatu hasznalata,
- composer gepelesi reszponzivitas javitasa,
- a jelenlegi UI es viselkedes megtartasa.

Elso korben nem cel:

- message list virtualizacio,
- history paging,
- Markdown renderer lecserelese,
- syntax highlighting vagy code viewer,
- streaming protokoll atalakitas,
- backend context guard attervezese.

## Fo hipotezis

A composer gepeles darabossaga akkor jelenhet meg, ha az `input` state valtozasa miatt a `ChatShell` ujrarenderel, es ezzel egyutt a `MessageThread` es a draga Markdown message bubble-ok is ujrarenderelodnek.

Ezt elso korben nem virtualizacioval, hanem render hatarok bevezetesevel erdemes kezelni.

## Tervezett lepesek

### Phase A - Meres es render hatarok

Cel:

- megerositeni, hogy input gepeleskor ujrarenderel-e a `MessageThread`,
- azonositani, mely propok valtoznak feleslegesen minden karakterleuteskor.

Lehetseges eszkozok:

- React DevTools Profiler manualisan,
- ideiglenes fejlesztoi render log csak lokalis tesztre,
- kodszintu prop stabilitas atnezes.

Kimenet:

- rovid dontes, eleg-e memoizacio, vagy szukseges komponensbontas.

### Phase B - `MessageThread` memoizacio

Cel:

- a teljes message thread ne renderelodjon ujra pusztan composer input valtozasra.

Javaslat:

- `MessageThread` exportjat `memo`-val vedeni,
- a callback propokat `useCallback`-kal stabilizalni ott, ahol ez szukseges,
- az objektum/array propok stabilitasat ellenorizni.

Kockazat:

- ha sok inline callback minden renderen uj referencia, a `memo` onmagaban nem segit,
- tul agressziv memo custom compare elrejthet valos UI frissitest, ezert elso korben ovatosan kell hasznalni.

### Phase C - Message bubble bontas es memoizacio

Cel:

- ha a `MessageThread`-nek frissulnie kell, ne renderelodjon ujra minden egyes uzenet.

Javaslat:

- kulon `MessageItem` vagy `MessageBubble` komponens,
- assistant Markdown tartalom kulon memoizalt komponensben,
- user bubble es recovery actionok kulon kezelese,
- pending assistant tovabbra is frissulhet streaming kozben.

Fontos:

- pending assistant streaming alatt normalis, hogy gyakran renderel,
- persisted assistant message-eknek viszont stabilnak kell maradniuk input gepeleskor.

### Phase D - Context char count optimalizalas

Cel:

- ne kelljen minden karakterleuteskor ujra vegigszamolni a teljes history szoveghosszat.

Javaslat:

- `historyCharCount` memoizalasa csak `activeMessages` valtozasra,
- `contextCharCount = historyCharCount + trimmedInput.length`,
- ezzel a composer gepeles kevesebb history bejarast vegez.

Megjegyzes:

- ez kisebb nyeres lehet, mint a Markdown rerender elkerulese,
- de olcso es koncepcionalisan tiszta.

### Phase E - Csak ha kesobb kell: virtualizacio

Ha nagyon hosszu chatfolyamoknal a memoizacio sem eleg:

- message list virtualizacio vizsgalata,
- csak lathato uzenetek renderelese,
- scroll-to-bottom es reasoning/live streaming osszehangolasa.

Ezt most korainak tekintjuk, mert bonyolultabb es tobb UI edge case-t hoz.

## Tesztterv

Automatizalt:

- `npm --prefix frontend run build`,
- backend teszt nem szukseges tisztan frontend render performance valtozasnal.

Manual smoke:

1. Hosszu chat history mellett composerbe gepeles nem darabosodik erezhetoen.
2. Assistant Markdown tartalmak nem tunnek el es nem renderelodnek hibasan.
3. Streaming assistant valasz tovabbra is folyamatosan jelenik meg.
4. Reasoning panel live es saved formaban is mukodik.
5. Scroll-to-bottom gomb es manual scroll override nem romlik.
6. Recovery user editor szerkesztes kozben alul marad, ha a user eleve alul volt.
7. Recovery user editor nem rangat vissza alulra, ha a user felgorgetett.

## Status

Status: Phase A/B/D es Phase C elso, kis kockazatu kore kesz; felhasznaloi proban a composer, recovery editor, live reasoning scroll es renderelt user buborek viselkedese javult.

Mar kesz:

- recovery editor alul-tartas fix,
- autosize textarea layout timing fix,
- `MessageThread` `memo` vedelme,
- stabil callback hatar `useStableCallback` hookkal a message thread actionokhoz,
- history karakter szamitas memoizalasa, hogy composer gepeleskor ne jarja be ujra a teljes chatfolyamot,
- `MessageItem` szintu memoizacio, hogy inline user-bubble szerkeszteskor csak az erintett uzenetsor renderelodjon ujra,
- frontend build sikeres a fixek utan,
- recovery editor scrollbar hover kurzora egyezik a composer textarea scrollbar viselkedesevel,
- live reasoning panel stabilabb bottom-follow mechanikat kapott ResizeObserver/requestAnimationFrame alapon,
- pending assistant typing indicator vegig lathato marad a stream befejezeseig,
- renderelt user buborek normalis szotorest es beljebb tartott belso scrollbart kapott.
- 2026-07-19 UI polish: teljes felulet es oldalsav color-page alapon, arnyekmentes gomb/panel stilus, masodlagos gomb hoverek a chat action gombokkal egységesítve, composer es rename input user-buborekhez igazodo hatterrel es azonos hover/focus border viselkedessel.

Kovetkezo javasolt lepes:

- tovabbi manual smoke hosszu chatfolyamon: saved reasoning, regenerate/retry actionok,
- ha meg mindig erezheto akadas marad, Phase C masodik kore: assistant Markdown tartalom kulon memoizalt rendererbe bontasa.
