# 018 - Assistant Response Duration

Statusz: implementalva; backend meres, DB mező, API schema es UI metaadat kijelzes kesz.

## Cel

Merjuk, taroljuk es jelenitsuk meg egy assistant valasz teljes generalasi idejet.

A meres kezdete: amikor a backend tenylegesen elinditja az adott assistant valasz modellhivasat.

A meres vege: amikor a backend a valaszt veglegesnek tekinti es elmenti. Streamelt valasznal ez a done/finalize pont, vagyis amikor a streambol megjott az utolso, mentendo assistant tartalom.

A megjelenites celja nem live stopperora, hanem egy mentett, utolag is lathato idoertek a valasz alatti action sorban, a masolas es ujrageneralas mellett.

## Termeknyelv

Javasolt formatum:

- 0:08
- 1:24
- 12:03

A UI-ban ne kapjon eros hangsulyt. Legyen harmadik, nem kattinthato meta elem a message action sorban.

## Alapelv

Backend oldalon merunk, nem frontend oldalon.

Indok:

- a meres perzisztens lesz,
- ujratoltes utan is megmarad,
- stream es non-stream utvonalon is egyseges,
- kesobb statisztikara is hasznalhato,
- nem fugg a bongeszo renderelesi utemezesetol.

A tenyleges kepernyore rajzolas utolso pillanata frontend oldali lenne, de termek szempontbol eleg jo kozelites a backend finalize ido. A felhasznaloi erzetet ez pontosan fogja kovetni nagyobb bonyolitas nelkul.

## Adatmodell

Az assistant_messages tabla bovuljon egy nullable mezovel:

- generation_duration_ms INTEGER vagy BIGINT

Javaslat: INTEGER eleg, mert milliszekundumban is nagy tartomanyt fed, de SQLAlchemy oldalon sima int legyen.

A mezo csak assistant uzeneteknel lesz ertelmezett. User uzeneteknel maradjon null.

## Backend Terv

### F1 - Schema Es Migration

- Alembic migration: uj nullable generation_duration_ms oszlop az assistant_messages tablara.
- SQLAlchemy model bovites.
- Pydantic response schema bovites.

Elfogadas:

- regi uzeneteknel az ertek null, a frontend ezt nem jeleniti meg.

### F2 - Meresi Pontok

A merest ott inditsuk, ahol az assistant valasz modellhivasa elkezdodik.

Stream utvonal:

1. A stream inditasakor backend oldalon start = perf_counter().
2. A stream done/finalize pontjan duration_ms = round((perf_counter() - start) * 1000).
3. finalize_streamed_assistant_message mentse az erteket.

Non-stream utvonal:

1. Modellhivas elott start = perf_counter().
2. Provider valasz utan, mentett assistant uzenet letrehozasakor szamoljuk a durationt.
3. Menteni kell generation_duration_ms mezobe.

Regenerate es retry:

- Ugyanugy merendo, mint normal send.
- Az uj assistant valasz sajat durationt kap.

Stop/abort eset:

- Ha nincs vegleges assistant uzenet, nincs mit merni.
- Ha kesobb reszleges valasz mentese bevezetodne, akkor kulon dontes kellene. Jelen tervben nem cel.

### F3 - Service Szerzodes

A service finalize/complete utvonalak kapjanak opcionalis generation_duration_ms erteket.

Fontos:

- a duration ne keruljon LLM contextbe,
- context guard ne szamolja,
- copy assistant answer ne tartalmazza,
- csak UI/meta adat.

## Frontend Terv

### F4 - Tipus Es Formatter

Frontend AssistantMessage tipus bovuljon:

- generation_duration_ms?: number | null

Keszitsunk kis formatter helper logikat:

- null vagy negativ ertek: ne jelenjen meg,
- 0-59999 ms: 0:SS,
- 60000 ms felett: M:SS,
- masodperc kerekites: emberi erzet szerint lehet Math.round(ms / 1000).

### F5 - Message Actions Megjelenites

A message action sorban, ahol jelenleg masolas es ujrageneralas van, jelenjen meg harmadik elemkent:

- nem gomb,
- nem kattinthato,
- visszafogott muted szin,
- formajaban illeszkedjen a tobbi meta elemhez,
- tooltip nem kotelezo.

Javasolt hely:

- masolas,
- ujrageneralas,
- idoertek.

Ha nincs duration, ne jelenjen meg ures hely.

## Tesztek

Backend:

- assistant response schema tartalmazza a duration mezot.
- stream finalize menti a kapott durationt.
- non-stream complete menti a durationt.
- user uzenet durationje None.
- _to_llm_messages nem hasznalja a duration mezot.

Frontend:

- formatter teszt, ha van helyi tesztminta.
- legalabb npm run build.

Manual smoke:

1. Kuldes normal modban: assistant valasz alatt megjelenik idoertek.
2. Excel/Adatbazis modban hosszabb toolos valasz: idoertek megjelenik es ujratoltes utan is megmarad.
3. Regenerate: az uj assistant valasz sajat idoerteket kap.
4. Regi uzeneteknel nincs hibas ures meta elem.

## Implementalt Allapot

- Uj nullable generation_duration_ms mezo kerult az assistant_messages tablara Alembic migracioval.
- A non-stream provider hivas es a stream finalize utvonal menti az assistant valasz sajat meresi idejet.
- Regenerate es retry stream utvonalon is uj meresi idot kap az uj assistant valasz.
- A frontend AssistantMessage tipus es a valasz alatti action sor megjeleniti az idoerteket M:SS formaban.
- Az ertek UI/metaadat, nem kerul vissza a modellkontextusba es nem resze a masolt valaszszovegnek.

## Elfogadasi Feltetelek

- Az assistant valaszokhoz mentett generation_duration_ms ertek tartozik uj valaszoknal.
- A frontend perc:masodperc formatumban jeleniti meg.
- Az ertek nem kerul vissza modellkontextusba.
- Stop/abort nem okoz hamis mentett durationt.
- Backend tesztek es frontend build zold.

## Parkolopalyan

- live UI stopperora stream kozben,
- token/sec vagy karakter/sec statisztika,
- provider/tool kulon bontott ido,
- conversation-level atlagok,
- performance dashboard.
