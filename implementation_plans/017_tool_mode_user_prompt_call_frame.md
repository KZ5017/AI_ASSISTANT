# 017 - Tool Mode User Prompt Call Frame

Statusz: implementalva; backend alapkor kesz, manual smoke kovetkezhet.

## Cel

Tool modokban rovid, aktualis hivasra vonatkozo user prompt keretet adjunk a modellnek, hogy a legutolso felhasznaloi kerdesnel is eros legyen a forrasellenorzesi irany.

A cel nem a mentett beszelgetes atirasa es nem a korabbi context osszekoszolasa. A cel kizarolag az, hogy a modellnek kuldott legutolso user uzenet kapjon egy rovid, tool-mode specifikus feladatkeretet.

## Kiindulasi Problema

Excel/Adatbazis modban elofordult, hogy a modell a korabbi final valaszok mintaja alapjan valaszolt, de a harmadik-negyedik korben mar nem hivott tenyleges Excel MCP eszkozt.

Pelda jelenseg:

- elso kerdesnel a modell forrasbol dolgozott,
- masodik kerdesnel szinten forrasbol dolgozott,
- harmadik pontositasnal csak az Excel eszkozlistat kerte le,
- tenyleges forras Excel hivas nelkul adott konkret adatvalaszt.

A munkanarracio artifact levalasztasa mukodik: a work_narration_content nem megy vissza contextbe. A problema tehat nem artifact-szivargas, hanem az, hogy a lokalis modell neha nem koveti eleg stabilan a tool-mode system promptot.

## Alapelv

A mentett user uzenet mindig maradjon tiszta, pontosan az, amit a felhasznalo beirt.

A modellnek kuldott aktualis hivasban viszont tool mod eseten a legutolso user uzenetet becsomagoljuk egy rovid instrukcios keretbe.

Ez a keret:

- nem kerul adatbazisba,
- nem jelenik meg UI-on user uzenetkent,
- nem kerul be kesobbi history-ba,
- csak az adott modellhivas payloadjaban el,
- csak tool modokban aktiv,
- csak a legutolso user uzenetre vonatkozik.

## Javasolt Keretek

Excel/Adatbazis mod:

Olvasd el az alabbi kerdest vagy utasitast:
{eredeti_user_uzenet}

MCP eszkoz hasznalataval olvasd el a 00-INDEX fajl tartalmat.
Az indexfajl tartalma es a kerdes vagy utasitas alapjan valaszd ki a megfelelo forrast.
A forras es a korabbi kontextus alapjan valaszold meg a kerdest vagy hajtsd vegre a kapott utasitast.

Obsidian/Tudasbazis mod:

Olvasd el az alabbi kerdest vagy utasitast:
{eredeti_user_uzenet}

MCP eszkoz hasznalataval olvasd el a 00-INDEX fajl tartalmat.
Az indexfajl tartalma es a kerdes vagy utasitas alapjan valaszd ki a megfelelo forrast.
A forras es a korabbi kontextus alapjan valaszold meg a kerdest vagy hajtsd vegre a kapott utasitast.

Normal mod:

Nincs prompt keret. A user uzenet valtozatlanul megy a modellnek.

## Fontos Hatarok

Nem cel:

- minden history user uzenetet becsomagolni,
- a mentett user promptot modositani,
- a UI-ban megjeleno user promptot modositani,
- backend oldalon valaszszoveget vagni vagy atirni,
- regexes forrasellenorzes,
- automatikus ujrakuldes vagy retry loop,
- tool-call kotelezosegi hibaval visszadobni a valaszt elso korben.

Cel:

- a legutolso user input kapjon eros, kozvetlen, munkautasitas jellegu forrasellenorzesi keretet,
- a korabbi context tovabbra is tiszta final assistant valaszokbol es eredeti user uzenetekbol alljon,
- az implementacio legyen olcso es konnyen visszafordithato.

## Implementacios Terv

### F1 - Tool Policy Bovites

A ToolModePolicy bovul opcionalis call_frame mezovel.

Peldak:

- excel: Excel forrasadat ellenorzesi keret,
- obsidian: vault-jegyzet ellenorzesi keret,
- none: nincs keret.

A keret legyen rovid es direkt. Ne tartalmazzon hosszu szabalylistat, mert a 9B modellnel a tul sok utasitas gyakran rontja a kovetkezetesseget.

### F2 - LLM Message Epites

A _to_llm_messages helper megkapja a tool policy call_frame erteket.

Logika:

1. A system prompt es tool prompt ugyanugy epul, mint korabban.
2. A messages listabol LLMChatMessage lista keszul.
3. Ha van call_frame, akkor csak a legutolso user uzenet contentje cserelodik keretezett valtozatra.
4. A bemeneti AssistantMessageModel objektumokat nem modositjuk.
5. A DB-ben es UI-ban tovabbra is az eredeti user content marad.

### F3 - Stream Es Non-stream Utvonalak

A modositas mindket utvonalra hat:

- send_message,
- regenerate_latest_assistant_message,
- prepare_send_message_stream,
- prepare_retry_last_user_message_stream,
- prepare_regenerate_message_stream.

Azert, mert mindegyik vegul modellhivast epit, es mindegyiknel a legutolso user utasitasra kell fokuszalni.

### F4 - Tesztek

Backend tesztek:

- Excel modban a providernek kuldott utolso user uzenet keretezett.
- A DB-ben mentett user uzenet eredeti marad.
- A kovetkezo modellhivasban a korabbi user uzenetek nem kapnak utolagos keretet.
- Normal modban nincs keretezes.
- Obsidian modban az Obsidian keret kerul a legutolso user uzenetre.
- Stream es non-stream utvonalon is ervenyesul.

Manual smoke:

1. Excel modban tobbkoros kerdes: M1HD azonos freki, majd HBO, majd Galaxi 4 HD.
2. Ellenorizni kell, hogy a harmadik korben is tortenik tenyleges Excel MCP hivas, nem csak eszkozlista lekeres.
3. UI-ban a user buborek tovabbra is csak az eredeti user promptot mutatja.
4. DB-ben a user content tovabbra is tiszta.

## Implementalt Allapot

- A ToolModePolicy opcionalis call_frame mezot kapott.
- Excel/Adatbazis modban a modellhivas legutolso user uzenete rovid altalanos forrasalapu keretet kap.
- Obsidian/Tudasbazis modban a modellhivas legutolso user uzenete rovid altalanos forrasalapu keretet kap.
- Normal modban nincs keretezes.
- A keret csak a providernek kuldott LLM payloadban el; a DB-ben es a UI-ban az eredeti user uzenet marad.
- Tobbfazisu utaknal is be van kotve: send, retry, regenerate, stream es non-stream.
- Backend tesztek fedik, hogy csak az aktualis legutolso user uzenet keretezett, a korabbi history es a mentett content tiszta marad.

## Ellenorzes

- cd backend && .venv/bin/python -m pytest -q - 64 passed, 1 warning.
- cd backend && .venv/bin/python -m ruff check app tests - All checks passed.

## Kockazatok

- A modell tovabbra is figyelmen kivul hagyhatja a keretet, mert lokalis kis modellrol van szo.
- A tul eros keret neha felesleges ujraellenorzest okozhat ott is, ahol a kontextusbol ertelmezni lehetne a kerdest.
- Ha a keret tul hosszu lesz, rontja a kovetkezetesseget. Ezert kell roviden tartani.

## Elfogadasi Feltetelek

- A mentett user uzenetek nem valtoznak.
- A providernek kuldott aktualis utolso user uzenet tool modban keretezett.
- A korabbi context nem koszolodik be.
- Legalabb egy tobbkoros Excel manual smoke stabilabban forrashivassal indul a harmadik-negyedik kerdesnel is.

## Visszagorgetes

A funkcio egy helyen kikapcsolhato legyen:

- call_frame mezok torlese vagy None-ra allitasa,
- illetve a helper visszaallitasa arra, hogy minden user contentet valtozatlanul adjon tovabb.

Mivel adatbazist nem erint, nincs migracio es nincs adattisztitasi feladat.
