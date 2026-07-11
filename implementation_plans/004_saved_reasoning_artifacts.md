# 004 - Saved Reasoning Artifacts

## Cel

A jelenlegi futas kozbeni reasoning_delta / Gondolatmenet UI annyira hasznos es kiforrott lett, hogy bizonyos feladatoknal erdemes lehet a reasoning tartalmat visszamenoleg is megorizni.

A cel nem az, hogy a reasoning a beszelgetes reszeve valjon a modell szemszogebol. A cel az, hogy emberi visszanezesre elerheto legyen, mikozben:

- nem kerul vissza a kovetkezo modellhivas kontextusaba,
- nem szamolodik bele a 120000 karakteres kontextusvedelembe,
- nem jelenik meg kulon chat uzenetkent,
- nem zavarja a vegleges assistant valaszt,
- alapbol csak kompakt, egysoros lenyithato blokk formajaban foglal helyet.

## Termekdontes

A reasoning legyen mentheto, de kontextusbol kizart mellektartalom.

Ez azt jelenti, hogy egy assistant uzenethez opcionalisan tartozhat mentett reasoning tartalom, de ez nem ugyanaz, mint az assistant valasz content mezoje.

Javasolt mentalis modell:

    assistant_message.content           -> vegleges assistant valasz, a chat kontextus resze
    assistant_message.reasoning_content -> opcionalis UI-only reasoning artifact, nem kontextus

## UX viselkedes

### Stream kozben

A mar meglevo elso koros reasoning UI marad:

- Gondolkodik allapot,
- Gondolatmenet lenyithato/osszecsukhato blokk,
- preview es expanded magassag,
- automatikus also kovetes,
- manual scroll override,
- Markdown render,
- whitespace normalizalas.

### Stream lezarta utan

Ha az assistant valaszhoz van mentett reasoning:

- a reasoning nem tunik el vegleg,
- a vegleges assistant valasz mellett/felett/alatt megjelenik egy kompakt egysoros blokk,
- alapbol osszecsukott,
- csak annyi helyet foglal, mint egy kis disclosure sor,
- lenyitva ugyanazt a reasoning renderelot hasznalja, mint stream kozben, de statikus modban.

Lehetseges label:

    Gondolatmenet

vagy kesobb:

    Gondolatmenet - 2431 karakter

A jelenlegi LM Studio-szeru minta alapjan az alapertelmezett allapot legyen kompakt es csukott.

## Kontextus szabaly

A mentett reasoning soha nem kerulhet be alapertelmezetten a modellnek kuldott history-ba.

Ez explicit invarians:

> Saved reasoning is a UI artifact, not chat context.

Kovetkezmenyek:

- a provider history osszeallitasakor csak role + content megy tovabb,
- reasoning_content ignoralt,
- a 120000 karakteres context guard nem szamolja bele,
- retry/regenerate sem hasznalja promptanyagkent,
- copy/regenerate alapertelmezesben tovabbra is csak a vegleges assistant valaszt kezeli.

## Adatmodell terv

### Backend model

Az assistant message tabla kapjon egy opcionalis mezot:

    reasoning_content: text | null

Javasolt nev: reasoning_content, mert egyertelmu es illeszkedik a frontend reasoningContent fogalomhoz.

### Alembic migracio

Uj migracio:

- nullable reasoning_content TEXT oszlop hozzaadasa az assistant messages tablazathoz,
- nincs backfill szukseg, regi uzeneteknel null.

### Schema/API

Az AssistantMessage response schema kapja meg:

    reasoning_content?: string | null

Frontend mapping:

    reasoning_content -> reasoningContent

A public API-ban ez olvashato adat legyen, de kuldeskor user payloadbol ne legyen irhato kozvetlenul.

## Streaming backend terv

A streaming vegpontok jelenleg reasoning_delta es delta esemenyeket kuldenek.

A stream kozben a backendnek ossze kell gyujtenie a reasoning delta-kat:

    reasoning_buffer += reasoning_delta.content
    assistant_buffer += delta.content

A stream sikeres befejezese utan az assistant message mentese:

    content = assistant_buffer
    reasoning_content = reasoning_buffer vagy null

Regenerate es retry eseten ugyanigy kell mukodnie.

### Abort/stop eset

Ha a user leallitja a streamet:

- ha nincs mentett assistant valasz, nincs mit reasoninggel parositani,
- a reasoning ilyenkor ne legyen kulon mentve,
- ha reszleges assistant valasz mentese kesobb bevezetodne, akkor ahhoz lehetne reszleges reasoninget is tarolni, de ez nem az MVP resze.

## Meretvedelem

Bar a reasoning nem szamit bele a kontextusba, DB/UI szempontbol megis kell vedeni.

Javaslat MVP-re:

- MAX_REASONING_SAVE_CHARS = 100000 vagy hasonlo,
- ha a reasoning hosszabb, menteskor levagas,
- opcionalis suffix:

    [... A gondolatmenet roviditve lett.]

Ez kesobb finomithato.

## Frontend terv

### Tipusok

AssistantMessage kapjon opcionalis mezot:

    reasoning_content: string | null

vagy frontend oldali camelCase mapping eseten:

    reasoningContent?: string | null

A PendingMessage.reasoningContent megmarad stream kozbeni allapotnak.

### Reasoning komponensek

A jelenlegi ReasoningPanel live mode-ra maradhat:

- Gondolkodik pulse,
- auto-scroll,
- manual override,
- stream kozbeni preview/expanded logika.

A persisted modhoz valoszinuleg tisztabb kulon komponens:

- SavedReasoningPanel,
- nincs Gondolkodik pulse,
- alapbol kompakt disclosure sor,
- lenyitva rendereli a mentett reasoninget,
- nem kell automatikus stream kovetes, csak normal scroll.

Ez tisztabb, mint egy tulfeltetelesitett kozos komponens.

### MessageThread render

Assistant message rendereles:

- pending assistant: live ReasoningPanel, ahogy most,
- persisted assistant, ha van reasoning_content: kompakt SavedReasoningPanel, majd vegleges Markdown valasz.

A persisted reasoning panel alapertelmezesben csukott legyen.

## Teszteles

### Backend

- streamelt valasz reasoning delta-val menti a reasoning_content mezot,
- reasoning nelkuli valasz null-t ment,
- history/provider payload nem tartalmazza a reasoninget,
- context guard nem szamolja bele,
- regenerate utan az uj assistant message uj reasoninget kap,
- stop/abort nem hoz letre arva reasoning artifactot.

### Frontend

- persisted assistant reasoning csukott disclosure-kent jelenik meg,
- lenyitva Markdown-kent renderel,
- nem jelenik meg, ha nincs reasoning,
- streaming alatti live panel tovabbra is mukodik,
- copy/regenerate gombok nem masoljak bele automatikusan a reasoninget.

## Implementacios lepesek

1. Backend adatmodell es Alembic migracio.
2. Backend schema bovitese reasoning_content mezovel.
3. Streaming service buffereles es mentes reasoningre.
4. Provider/context builder ellenorzes: reasoning explicit kizart.
5. Backend tesztek a mentesre es context-kizarasra.
6. Frontend API tipus bovitese.
7. SavedReasoningPanel komponens letrehozasa kompakt disclosure UI-val.
8. MessageThread persisted assistant rendering bekotese.
9. Frontend build es manual smoke.
10. Allapotdoksik frissitese, ha a funkcio elkeszul.

## Nyitott dontesek

- Pontos maximum mentheto reasoning meret: 50000 vagy 100000 karakter?
- A kompakt sor mutasson-e karakterhosszt?
- A saved reasoning helye az assistant valasz felett vagy alatt legyen? Jelenlegi javaslat: felette, mert stream kozben is ott jelenik meg.
- Legyen-e kulon copy reasoning gomb? MVP-ben nem.

## Statusz

MVP implementalva es felhasznaloi proban jonak itelve. A backend menti a streaming reasoning tartalmat assistant message mellektartalomkent, a context builder tovabbra is kizarja, a frontend pedig csukott SavedReasoningPanel disclosure-kent jeleniti meg a perzisztalt reasoninget.

Ellenorizve: Alembic migracio lefutott, `assistant_messages.reasoning_content` oszlop megvan, backend/frontend ujrainditva, `pytest -q` 32 passed, `ruff check app tests` passed, `npm run build` passed.

Kesobbi finomitas lehet a pontos maximum meret, a karakterhossz kijelzese es opcionális kulon copy reasoning gomb.
