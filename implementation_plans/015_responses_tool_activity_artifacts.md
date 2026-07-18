# 015 - Responses Tool Activity Artifacts

Statusz: implementalva; F1-F6 kesz, F7 opcionális prompt-finomítás parkolopalyan.

## Cel

A `lm_studio_responses` provider alatt a modell MCP/tool hasznalathoz kapcsolodo tevekenysegei valjanak el a vegleges assistant valasztol.

A cel nem az, hogy a backend szoveget vagdosson vagy utolag kitalalja, mi volt munkanaplo. A cel az, hogy a `/v1/responses` API altal eleve strukturaltan kulon adott MCP/tool eventeket kulon app-szintu stream es adatmodell artifactkent kezeljuk.

Termekoldali eredmeny:

- a vegleges assistant valasz tisztabb marad,
- a tool/MCP tevekenyseg lathato lehet egy kulon UI dobozban,
- a tool activity nem kerul vissza a kovetkezo modellhivas kontextusaba,
- a reasoning es tool activity egymastol fuggetlenul, de egymas mellett tud megjelenni.

## Hivatkozasok

- `011_lm_studio_responses_mcp_notes.md` - kutatasi jegyzet: a `/v1/responses` streaming alatt kulon `response.mcp_list_tools.*` es `response.mcp_call.*` eventek jelentek meg.
- `012_llm_provider_abstraction_and_responses_provider.md` - Responses provider terv: a tool/MCP lifecycle eventek jelenleg internal/status jelleggel vannak kezelve.
- `004_saved_reasoning_artifacts.md` - minta arra, hogyan kezelunk UI-only, kontextusbol kizart assistant artifactot.

## Alapdontesek

1. A feature csak `lm_studio_responses` provider alatt tud teljes erteku lenni.
2. A native LM Studio provider alatt nincs megbizhato, strukturalt tool event szetvalasztas; ott ez a feature inaktiv vagy ures marad.
3. A backend nem vag ki es nem ir at `response.output_text.delta` tartalmat.
4. A vegleges assistant valasz tovabbra is kizarolag a final answer content.
5. Tool activity csak API-szintu strukturalt MCP/tool eventbol keletkezhet.
6. A tool activity UI artifact, nem chat context.
7. A tool activity mentheto, de nem kuldheto vissza kovetkezo modellhivas history-jaba.

## Mit tekintunk tool activitynek

Responses stream alatt tool activity forras lehet:

- `response.mcp_list_tools.*`,
- `response.mcp_call.*`,
- `response.output_item.added` es `response.output_item.done`, ha az `item.type` erteke `mcp_list_tools` vagy `mcp_call`,
- kesobbi LM Studio/OpenAI-kompatibilis tool lifecycle eventek, ha azonos szerepuek.

Ezekbol az app sajat normalizalt eventet kepezhet.

Javasolt app-szintu event tipus:

```python
LLMStreamEvent(type="tool_activity", content="...", raw=payload)
```

A `content` emberi olvasasra alkalmas rovid szoveg legyen, de a `raw` maradjon elerheto backend oldali feldolgozashoz vagy teszthez.

## Mit nem tekintunk tool activitynek

Nem tool activity:

- a modell altal sima `response.output_text.delta` formaban generalt szoveg, peldaul: "Megnezem a fajlt...",
- vegleges valasz reszekent erkezo magyarazat,
- reasoning delta,
- frontend oldali kovetkeztetes vagy regexes szovegreszlet.

Ha a modell munkanaplot ir a vegleges valaszba, azt prompttal kell finomitani. Backend oldali szovegvagas tilos.

## Mentalis modell

Egy assistant uzenethez harom kulon tartalom tartozhat:

```text
assistant_message.content               -> vegleges assistant valasz, chat context resze
assistant_message.reasoning_content     -> UI-only Gondolatmenet artifact, nem context
assistant_message.tool_activity_content -> UI-only Eszkozhasznalat artifact, nem context
```

A kovetkezo modellhivas history-jaba csak `role + content` kerulhet.

## UX terv

### Stream kozben

Ha tool activity event erkezik:

- jelenjen meg egy kulon kompakt doboz a reasoninghez hasonlo mintaval,
- cime legyen `Eszközhasználat`,
- allapot szovege lehet `Eszközök használata` vagy `Adatforrások ellenőrzése`,
- ikon: `FileSearch` vagy `Wrench`, mert altalanosabb, mint a kalapacs,
- szinvilag: reasoningtol elkulonulo, szolid kekes tokenalapu tema.

A doboz ne versenyezzen a final valasszal. A cel az atlathatosag, nem egy masodik chatvalasz.

### Reasoninggel egyutt

Ha reasoning es tool activity is erkezik, ket kulon blokk jelenjen meg:

1. `Gondolatmenet`
2. `Eszközhasználat`
3. vegleges assistant valasz

A sorrend UX-dontes, de javasolt a reasoning felul, tool activity alatta, mert a tool activity kozelebb van a kulso adatforrasokhoz.

### Stream utan

Ha az assistant valaszhoz van mentett tool activity:

- jelenjen meg kompakt, alapbol csukott disclosure blokkban,
- ne foglaljon sok helyet,
- lenyitva latszodjon az eszkoztevekenyseg rovid listaja vagy renderelt naploja,
- a blokk ne keruljon a copy assistant answer alapertelmezett tartalmaba.

## Tool activity tartalomforma

Elso korben egyszeru szoveges artifact eleg.

Javasolt normalizalt sorok:

```text
Eszközlista lekérése: excel
Eszközhívás: lookup_excel_rows
Eszközhívás kész: lookup_excel_rows
```

Ha az event payload tartalmaz tool nevet, server labelt vagy statuszt, azt roviden meg lehet jeleniteni.

Fontos: a tool output teljes nyers tartalmat nem feltetlenul kell megjeleniteni, mert nagy es zajos lehet. Elso korben eleg a lifecycle-szintu osszefoglalo.

### Gazdagitott tartalomforma

A 2026-07-18-i raw Responses stream mintavetel alapjan a `response.mcp_call.*` lifecycle eventek onmagukban szegenyesek, viszont a kapcsolodo `response.output_item.added/done` eventek `item` objektuma hasznos strukturalt mezoket tartalmaz:

- `item.server_label`, peldaul `excel`,
- `item.name`, peldaul `describe_excel_sheet`, `filter_excel_rows`,
- `item.arguments`, JSON stringkent, peldaul `filepath`, `sheet_name`, `filter_column`, `filter_value`, `lookup_column`, `lookup_value`,
- `item.output`, tool valasz text payloadkent, amely sok esetben JSON stringet tartalmaz,
- `item.status`, peldaul `in_progress` vagy `completed`.

A gazdagitott UI naplo celja nem a teljes tool output dumpolasa, hanem rovid, emberi diagnosztikai sorok kepzese strukturalt mezokbol. Pelda:

```text
Excel eszköz: describe_excel_sheet
Fájl: 00-INDEX.xlsx, munkalap: FILES

Excel eszköz: filter_excel_rows
Fájl: Csatornakiosztas_tiszta.xlsx, munkalap: Kombi_tábla_26-04-10
Szűrés: HBO Pak = x
Találat: 3 sor
```

A backend tovabbra sem vaghat ki szoveget a final answerbol, es nem probalhatja a modell sima narraciojat tool naplova alakitani. Csak strukturalt Responses eventbol dolgozhat.

### Aktualis Markdown forma

Az Eszkozhasznalat artifact tartalma strukturalt Markdown listakent generalodik, nem CSS-szel utolag formazott bekezdeshalmazkent.

Pelda:

```md
- *Excel eszköz indult:* `lookup_excel_rows`
- **Excel eszköz:** `lookup_excel_rows`
  - Fájl: `Csatornakiosztas_tiszta.xlsx`, munkalap: `Kombi_tábla_26-04-10`
  - Keresés: `Program update: 2026-04-10 = HBO` (részszöveg)
  - Találat: **3 sor**
```

Dontes:

- a backend egy-egy tool activity eventet listaitemkent ad,
- a frontend es a mentett artifact egyszeres newline-nal fuzi ossze az eventeket,
- nincs `\n\n` alapu bekezdes-tavolsag gyartas,
- nincs tool-activity-specifikus paragraph spacing CSS hack,
- a listastruktura adja a live es mentett doboz olvashato sortoreseit.
- a live tool activity ikon tovabbra is pulzalhat folyamat kozben, de a mentett/statikus SavedToolActivityPanel ikonja animacio nelkul jelenik meg, a saved reasoning panellel egységesen.

## Backend implementacios terv

### F1 - Stream event tipus bovites

Statusz: kesz.

Feladatok:

- `LLMStreamEvent` tipus bovitese `tool_activity` lehetoseggel,
- Responses parserben `response.mcp_list_tools.*` es `response.mcp_call.*` mapping `tool_activity` eventre,
- native provider tovabbra sem gyart ilyen eventet,
- unit tesztek rogzitett Responses SSE mintaval.

Elfogadas:

- Responses stream alatt tool eventbol app-szintu `tool_activity` jon,
- `output_text.delta` valtozatlanul `message_delta`,
- `reasoning_text.delta` valtozatlanul `reasoning_delta`,
- nincs final answer szovegvagas.

### F2 - Backend SSE szerzodes

Statusz: kesz.

Feladatok:

- assistant router SSE generator kezelje a `tool_activity` eventet,
- frontend fele kuldjon kulon SSE eventet,
- a normal message delta, reasoning delta, done flow ne valtozzon.

Javasolt frontend event:

```text
event: tool_activity
data: { "content": "..." }
```

Elfogadas:

- frontend parser nem esik el ismeretlen eventen,
- uj event tipizalva van,
- regi native provider mellett nem jelenik meg ures vagy hibas tool activity.

### F3 - Adatmodell es mentes

Statusz: kesz.

Feladatok:

- `assistant_messages` tabla bovitese nullable `tool_activity_content` TEXT mezovel,
- schema/API response bovitese `tool_activity_content` vagy frontend camelCase `toolActivityContent` mezovel,
- streamed finalization gyujtse es mentse az osszefuzott tool activity tartalmat,
- non-stream Responses hivasnal elso korben nem kotelezo tool activity mentes, mert ott nincs ugyanaz a live SSE granularitas; kesobb bovithetjuk.

Megvalositas:

- `assistant_messages.tool_activity_content` nullable TEXT oszlop Alembic migracioval bekerult.
- `AssistantMessageResponse` es frontend `AssistantMessage` tipus tartalmazza a `tool_activity_content` mezot.
- A stream router a `tool_activity` SSE eventeket kulon gyujti es `finalize_streamed_assistant_message` menteskor newline-szeparalt artifactkent tarolja.
- `_to_llm_messages` es a context guard tovabbra is csak `message.content` mezovel dolgozik, igy a tool activity nem megy vissza modellkontextusba.
- A saved assistant uzenet a final valasz felett alapbol csukott `SavedToolActivityPanel` blokkban tudja megjeleniteni az artifactot.

Elfogadas:

- mentett assistant uzenethez visszanyithato tool activity tartozhat,
- `_to_llm_messages` nem hasznalja a tool activity mezot,
- context guard nem szamolja bele,
- retry/regenerate nem kuldi vissza.

### F4 - Frontend stream allapot

Statusz: kesz.

Feladatok:

- stream parser bovites `tool_activity` eventre,
- `ChatShell` pending assistant allapotban kulon gyujtse a tool activity contentet,
- `MessageThread` kapja meg es jelenitse meg pending/mentett allapotban,
- stop/abort es error utan is stabilan takaritson.

Elfogadas:

- stream kozben megjelenik az Eszkozhasznalat doboz,
- final valasz tovabbra is kulon epul,
- abort utan nincs UI beragadas,
- normal chat tool nelkul nem mutat ures dobozt.

### F5 - Tool Activity UI komponens

Statusz: kesz.

Feladatok:

- reasoning panel mintajara uj komponens vagy parametrizalt kozos disclosure komponens,
- label: `Eszközhasználat`,
- ikon: `FileSearch` vagy `Wrench`,
- kekes tokenalapu szinvaltozat,
- kompakt/expanded allapot,
- scroll viselkedes a reasoning box mintajara,
- saved artifact alapbol csukott.

Elfogadas:

- reasoning es tool activity egyszerre is olvashato,
- UI nem tolja szet a chatfolyamot indokolatlanul,
- mobilon sem log ki,
- sotet es vilagos modban is olvashato.

### F6 - Gazdagitott tool activity event feldolgozas

Statusz: kesz.

Feladatok:

- Responses parser kezelje a `response.output_item.added` es `response.output_item.done` eventeket, ha `item.type` `mcp_call` vagy `mcp_list_tools`.
- A tool activity szoveget elsodlegesen az `item` objektumbol kepezze, ne a szegenyes lifecycle eventbol.
- `mcp_call` esetben hasznalja: `server_label`, `name`, `status`, `arguments`.
- Az `arguments` JSON stringet strukturaltan parse-olja, de ha hibas vagy nem objektum, essen vissza rovid nyers jelzesre.
- `output` mezobol csak kis, biztonsagos osszefoglalo keruljon a UI-ba, peldaul `matches`, `row_count`, `sheet_name`, `used_range`, nem teljes sorlista vagy nagy JSON dump.
- Az in-progress es completed eventeket ne duplazza zajosan: cel, hogy egy tool hivashoz legfeljebb egy indulasi es egy lezaro/informativ sor jelenjen meg.
- A parser tartsa meg a `raw` payloadot tesztelhetoen, de a frontend tovabbra is csak a normalizalt `content` mezot jelenitse meg.

Javasolt normalizalas:

- `mcp_list_tools` added/done: listaitem `Excel eszközlista lekérése` / `Excel eszközlista elérhető`
- `mcp_call` added: listaitem `Excel eszköz indult: <tool_name>`
- `mcp_call` done: listaitem + beagyazott reszletlista:
  - `Excel eszköz: <tool_name>`
  - `Fájl: <filepath>` ha van
  - `Munkalap: <sheet_name>` ha van
  - `Keresés/Szűrés/Összesítés: ...` az ismert argumentumkulcsokbol
  - `Találat: <matches> sor` ha az outputbol biztonsagosan kiolvashato

Elfogadas:

- A tool doboz nem csak `Eszközhívás (completed)` sorokat mutat, hanem a hasznalt toolt es legalabb a fajl/munkalap/kereses lenyeget.
- Nincs final answer szovegvagas.
- Nincs teljes tool output dump a UI-ba.
- Mentett `tool_activity_content` mar a gazdagitott sorokat tarolja.
- Unit teszt rogzit legalabb egy `response.output_item.done` mcp_call eventet `arguments` es `output` mezokkel.

Megvalositas:

- A Responses parser `response.output_item.added/done` alatt felismeri az `mcp_list_tools` es `mcp_call` itemeket.
- A korabbi `response.mcp_*` lifecycle eventek statuskent kezelodnek, hogy ne duplazzak zajosan a UI naplot.
- A normalizalas az `item.name`, `item.server_label`, parse-olt `arguments` es kicsi, biztonsagos `output` osszefoglalo alapjan keszul.
- Teljes tool output dump nincs; a UI-ba csak rovid diagnosztikai sorok kerulnek.
- Célzott unit teszt frissitve a gazdagitott `output_item.done` payloadra.

### F7 - Prompt finomitas

Statusz: opcionális parkolopalyan, jelenleg nem szukseges.

Feladatok:

- Excel/Obsidian tool mode promptokban finoman kerni, hogy a modell ne irjon munkanaplot a vegleges valaszba,
- a prompt ne legyen tul hosszu vagy tulszabalyozott,
- backend tovabbra sem vag szoveget.

Javasolt elv:

```text
A végső válaszban ne írd le részletesen az eszközhasználat lépéseit; csak a választ és rövid forrásmegjelölést add meg.
```

Ezt csak akkor erdemes bevezetni, ha a gazdagitott strukturalt tool activity UI mellett meg mindig tul sok munkanaplo kerul a final answerbe.

## F4-F5 live UI zaras

Megvalositva:

- uj `ToolActivityPanel` komponens `Eszközhasználat` labellel es `FileSearch` ikonnal,
- pending assistant alatt a reasoning blokk utan megjelenik az eszkoztevekenyseg blokk, ha van `toolActivityContent`,
- a panel auto-scroll es kompakt/nyithato viselkedest kapott a reasoning mintajara,
- a vizualis stilus kekes, elkulonul a reasoning narancsos karakteretol,
- mentett tool activity artifact adatbazis mezovel es alapbol csukott saved panellel megvalosult.

Ellenorzes:

- `cd frontend && npm run build` - passed,
- `cd backend && .venv/bin/python -m pytest tests/test_lm_provider.py tests/test_assistant_persistence.py` - 49 passed.

## F1-F2 zaras

Megvalositva:

- Responses parser MCP lifecycle eventbol `tool_activity` eventet kepez,
- backend SSE kulon `tool_activity` eventet kuld,
- frontend stream parser es handler szerzodes felismeri az uj eventet,
- a frontend gyujti a pending assistant `toolActivityContent` erteket; a lathato UI doboz es a mentes kesobbi F3-F5 lepesben megvalosult,
- final answer szovegvagas nincs, `output_text.delta` tovabbra is `message_delta`.

Ellenorzes:

- `cd backend && .venv/bin/python -m pytest tests/test_lm_provider.py tests/test_assistant_persistence.py` - 49 passed,
- `cd frontend && npm run build` - passed.

## Tesztelesi terv

Backend:

- Responses parser `mcp_list_tools` event -> `tool_activity`,
- Responses parser `mcp_call` event -> `tool_activity`,
- `output_text.delta` nem kerul tool activitybe,
- stream finalization menti a tool activity artifactot,
- `_to_llm_messages` nem kuldi vissza a `tool_activity_content` mezot,
- context guard nem szamolja bele.

Frontend:

- stream parser felismeri a `tool_activity` eventet,
- pending assistant tool activity doboz megjelenik,
- saved assistant tool activity doboz megjelenik,
- reasoning + tool activity egyutt mukodik,
- tool nelkuli normal valasznal nincs ures doboz.

Manual smoke:

1. Responses provider, normal chat tool nelkul: nincs Eszkozhasznalat doboz.
2. Responses provider, Excel/Adatbazis mod: Eszkozhasznalat doboz megjelenik, final valasz kulon epul.
3. Responses provider, Tudasbazis mod: ha remote MCP mukodik, Obsidian tool activity kulon jelenik meg.
4. Reasoning + Excel egyszerre: Gondolatmenet es Eszkozhasznalat kulon dobozban latszik.
5. Masodik user uzenet ugyanabban a chatben: tool activity nem kerul vissza prompt history-ba.

## Kockazatok

- Az LM Studio Responses event nevei verziofuggok lehetnek.
- Tool output nagy lehet, ezert elso korben nem szabad teljes nyers outputot automatikusan UI-ba onteni.
- A modell tovabbra is irhat munkanaplot a final answerbe; ezt csak prompttal erdemes kezelni.
- Native provider alatt nincs paritas, ezert a feature provider-specifikus.

## Nem cel

- Backend oldali final answer szovegvagas.
- Regexes magyar/angol munkanaplo-felismeres.
- Teljes tool audit rendszer.
- Tool input/output teljes mentese MVP-ben.
- UI provider-valto kapcsolo.
- Native provider MCP event szetvalasztasa.

## Parkolopalya

- Tool-call timeline UI.
- Tool output reszletek lenyithato megjelenitese.
- Tool activity copy gomb.
- Tool activity szuro: csak hibak / minden event.
- Obsidian es Excel tool activity kulon ikon vagy label.
- Kesobbi OpenAI felhos Responses provider azonos artifact szerzodessel.

## Aktualis zaras

A terv szerinti MVP kesz:

- Responses provider alatt az MCP/tool activity kulon `tool_activity` stream eventkent jon,
- live es mentett `Eszközhasználat` dobozban jelenik meg,
- a mentett artifact `assistant_messages.tool_activity_content` mezoben van,
- nem kerul vissza a kovetkezo modellkontextusba,
- a vegleges assistant valaszt a backend nem vagja es nem faragja,
- a gazdagitott tool activity lista technikailag es UI-ban is felhasznaloi proban jonak bizonyult.

Kovetkezo munka csak konkret hasznalati visszajelzes alapjan indokolt. F7 prompt-finomitas es timeline/copy/szuro jellegu extrak parkolopalyan maradnak.
