# 016 - Responses Final Answer Separation

Statusz: implementalva; backend es frontend alapkor kesz.

## Cel

A lm_studio_responses provider alatt a modell toolhasznalat kozbeni sima szoveges munkanarracioja valjon le a tenyleges vegleges assistant valaszrol.

A cel nem live stream buffereles es nem regexes szovegvagas. Elso korben a stream kozbeni UI viselkedes maradhat a jelenlegi: amit a modell response.output_text.delta formaban kuld, az lathatoan streamelhet.

A cel a stream vegen, a response.completed strukturalt response.output listaja alapjan torteno tiszta mentes:

- assistant_message.content csak a tenyleges vegleges valasz legyen,
- a toolhasznalat kozbeni munkanarracio kulon UI-only artifactkent megmaradhat,
- a kovetkezo modellhivas contextjebe csak a vegleges valasz keruljon vissza,
- a felhasznalo ne veszitse el azt, amit stream kozben latott.

## Kiindulasi Megfigyeles

A 2026-07-19-i raw Responses stream vizsgalat az alabbi kerdesen tortent, reasoning off mellett:

Kerlek sorold fel az M1HD csatornaval azonos frekin levo csatornakat

A nyers streamben a modell munkanarracioja es a vegso valasz is response.output_text.delta eventkent erkezett, tehat delta-szinten nem valaszthato szet biztonsagosan.

A response.completed.response.output viszont strukturalt itemlistat tartalmazott. A minta 18 output itemet adott:

- mcp_list_tools,
- tobb message item munkanarracioval,
- tobb mcp_call,
- vegul egy utolso message item a tenyleges valasszal.

Kovetkeztetes:

- stream kozben azonnali, biztos final/narracio szetvalasztas csak bufferelessel lenne lehetseges,
- stream utan viszont a teljes strukturalt output lista alapjan stabilan kinyerheto az utolso type == message item,
- ezt tekintjuk elso korben a final assistant valasznak.

## Hatarok

Elso korben cel:

- csak lm_studio_responses providerre vonatkozzon,
- stream kozben ne vezessunk be live bufferelest,
- ne vagjunk szoveget regexszel,
- ne probaljuk nyelvi mintak alapjan felismerni a munkanarraciot,
- a final mentett content a response.completed.response.output utolso message itemjebol szarmazzon,
- a korabbi message itemek kulon, contextbol kizart artifactkent mentodjenek.

Elso korben nem cel:

- a live UI-bol eltuntetni a munkanarraciot,
- kesleltetett final-answer streaming,
- prompt alapu forras vagy narracio tiltogatas,
- native provider viselkedesen valtoztatni,
- tool activity artifactot osszekeverni a munkanarracioval.

## Mentalis Modell

assistant_message.content
  A tenyleges vegleges assistant valasz. Context resze.

assistant_message.reasoning_content
  UI-only Gondolatmenet artifact. Nem context.

assistant_message.tool_activity_content
  UI-only Eszkozhasznalat artifact strukturalt MCP/tool eventekbol. Nem context.

assistant_message.work_narration_content
  UI-only Responses munkanarracio artifact a final valasz elotti message itemekbol. Nem context.

A work_narration_content nev csak javaslat. Implementacional valaszthato mas nev, ha jobban illik a kodbazisba, peldaul response_narration_content vagy assistant_activity_content.

## Dontesek

1. A final answer forrasa Responses provider alatt a response.completed.response.output utolso message itemje.
2. Ha nincs ilyen item, a provider adjon ertelmes hibat, vagy fallbackeljen a korabbi Responses final content logikara csak explicit dontessel.
3. A final answer elotti message itemek munkanarracionak minosulnek.
4. A munkanarracio mentheto, de nem mehet vissza a kovetkezo modellhivas history-jaba.
5. A munkanarracio nem tool activity: nem MCP eventbol jon, hanem modell altal generalt message itemekbol.
6. A stream kozbeni jelenlegi lathatosag elso korben megmarad.
7. Copy assistant answer tovabbra is csak a final content legyen, ne tartalmazza a munkanarraciot.

## Backend Terv

### F1 - Responses Output Item Helper

Feladat:

- keszuljon provider oldali helper, amely a response.completed payloadbol visszaadja:
  - final_content,
  - work_narration_content,
  - opcionálisan a message itemek szamat es diagnosztikai adatokat teszthez.

Javasolt logika:

1. Olvasd ki a response.output listat.
2. Gyujtsd ki sorban azokat az itemeket, ahol item.type == message.
3. Minden message itembol ugyanazzal a tartalomkinyeressel vedd ki a szoveget, mint amit a Responses final content helper hasznal.
4. Az utolso nem ures message text legyen final_content.
5. Az ezt megelozo nem ures message textek newline-nal vagy egyszeru Markdown formatumban alkossak a work_narration_content artifactot.

Elfogadas:

- a raw M1HD mintan az utolso tablazatos valasz kerul final contentbe,
- az elotte levo munkalepes jellegu uzenetek nem kerulnek final contentbe,
- nincs regex vagy magyar szovegminta alapu vagdosas.

### F2 - Stream Event Szerzodes Bovites

Feladat:

- LLMStreamEvent bovuljon opcionális work_narration_content mezovel, vagy vezessunk be uj event tipust a stream vegen.
- response.completed feldolgozasakor a done event tartalmazza a final contentet es a munkanarracio artifactot.

Fontos:

- a message_delta stream kozben elso korben valtozatlanul mehet,
- a final mentest a done.final_content erteknek kell felulirnia, ha a router jelenleg aggregalt deltat mentene.

Elfogadas:

- a stream kozbeni UI nem torik,
- a done.final_content mar csak az utolso message item,
- a router hozzafer a munkanarracio artifacthoz.

### F3 - Adatmodell Es Persistence

Feladat:

- assistant_messages tabla bovuljon nullable TEXT mezovel a munkanarracio artifactnak.
- SQLAlchemy model, schema es frontend tipus bovuljon.
- finalize_streamed_assistant_message mentse a mezot.
- _to_llm_messages es context guard tovabbra is csak content mezot hasznaljon.

Elfogadas:

- mentett assistant uzenetben a final content tiszta,
- munkanarracio visszanyithato UI-only artifact,
- kovetkezo modellhivas history-jaban nincs munkanarracio,
- context guard nem szamolja bele.

### F4 - Frontend UI Artifact

Feladat:

- legyen kompakt, alapbol csukott disclosure a final valasz felett vagy a tool activity mellett.
- A stilus illeszkedjen a Gondolatmenet es Eszkozhasznalat dobozokhoz, de ne legyen azonos a tool activityvel.
- Cim javaslatok:
  - Munkalepesek,
  - Munkamenet,
  - Feldolgozas.

Javasolt termeknyelv: Munkalepesek.

Megjelenitesi sorrend javaslat:

1. mentett reasoning, ha van,
2. mentett eszkozhasznalat, ha van,
3. mentett munkalepesek, ha van,
4. final assistant valasz.

A pontos sorrend UX dontes; implementacio elott erdemes roviden megerositeni.

Elfogadas:

- user lathatja, amit stream kozben latott,
- final valasz kulon es tisztan olvashato,
- copy final valasz nem tartalmazza a munkalepeseket.

### F5 - Tesztek

Backend unit:

- Responses completed payload tobb message + mcp_call itemmel:
  - final content = utolso message,
  - work narration = korabbi message itemek,
  - tool activity tovabbra is kulon.
- Egyetlen message itemes payload:
  - final content = az egyetlen message,
  - work narration = None.
- Ures vagy hibas message itemek:
  - nem okoznak hamis artifactot.
- _to_llm_messages nem kuldi vissza az uj artifact mezot.

Frontend/build:

- npm run build.

Manual smoke:

1. Excel modeban M1HD/freki kerdes.
2. Stream kozben a jelenlegi viselkedes megmarad.
3. Stream utan a mentett final valasz csak a tenyleges valasz.
4. A munkalepesek visszanyithato dobozban megvannak.
5. Ujabb kerdesnel a modell nem kapja vissza a munkalepeseket contextkent.

## Kockazatok

- Az utolso message item = final answer feltetelezes eros, de a jelenlegi Responses raw mintan ez latszik. Tovabbi smoke javasolt Obsidian es Excel modban is.
- Ha a provider kesobb mas output strukturetat ad, unit tesztekkel gyorsan eszreveheto.
- Stream kozben a user tovabbra is lathat munkanarraciot; ez tudatos elso kori kompromisszum.

## Parkolopalyan

- live buffereles, ha kesobb a munkanarraciot stream kozben sem akarjuk mutatni,
- kulon kapcsolo a munkalepesek megjelenitesere,
- munkalepesek kulon copy gomb,
- munkalepesek es tool activity egyesitett timeline UI.


## Implementalt Allapot

- A Responses provider a response.completed strukturalt output listajabol az utolso message itemet menti vegleges assistant valaszkent.
- Az ezt megelozo message itemek work_narration_content mezobe kerulnek, UI-only artifactkent.
- A normal es streamelt send/regenerate utak mentik az uj mezot.
- A kovetkezo modellhivas history-ja tovabbra is csak az assistant_message.content mezot hasznalja, igy a munkalepesek nem mennek vissza contextbe.
- A frontend mentett, alapbol csukott Munkalepesek panelben jeleniti meg az artifactot.
- Backend unit tesztek es frontend build lefutottak.
