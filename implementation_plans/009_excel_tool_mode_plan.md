# 009 - Excel / Adatbazis Tool Mode Implementation Plan

## Cel

Ez a dokumentum az Excel-alapu Adatbazis tool mode konkret viselkedeset es implementacios tervet rogziti.

A terv a kovetkezo dokumentumokra epul:

- 005_mcp_tool_modes_direction.md - magas szintu MCP/tool mode alapvetesek,
- 006_tool_mode_foundation_plan.md - kozos backend/frontend tool mode foundation,
- 007_obsidian_tool_mode_plan.md - konkret tool mode minta Obsidian/Tudasbazis modhoz.

Ez a dokumentum nem altalanos spreadsheet automatizalasi terv, nem Excel szerkeszto UI terv, es nem tobb tool egyideju hasznalatanak terve. Kizarolag azt rogziti, hogy az Excel-alapu eszkozmod hogyan illeszkedjen a jelenlegi standalone AI Assistant alkalmazasba a mar mukodo MCP/tool mode foundation mintajara.

## Kiindulo termekdontes

Az elso Excel tool mode celja nem az, hogy a felhasznalo altalanos Excel szerkeszto AI-t kapjon.

Az elso kor celja:

- Excel fajlokban es munkalapokon tarolt informaciok elerese,
- kerdes-valasz jellegu informaciokinyeres tablazatokbol,
- a felhasznalo megkimelese attol, hogy kezzel megnyissa, atnezze es keresse az adatokat,
- a modell szigoru iranyitasa arra, hogy a valaszhoz az Excel tablazatokat hasznalja forraskent.

Termekanalogianak az Obsidian/Tudasbazis mod tekintendo:

- Tudasbazis = Obsidian / Markdown vault,
- Adatbazis = Excel tablazatok,
- mindketto explicit user altal valasztott tool mode,
- a user dolga tudni, hogy a keresett informacio melyik forrasvilagban talalhato,
- az app dolga a megfelelo backend policy, integration es prompt context biztositas.

A user-facing nev elso korben: Adatbazis.

A motorhazteto alatt Excel MCP server es LM Studio integration mukodik, de ezt a felhasznaloi UI nem magyarazza tul.

## Jelenlegi bizonyitott allapot

Az Excel MCP integraciohoz szukseges fo puzzle darabok mar bizonyitottan megvannak:

- a valasztott Excel MCP server venv-ben telepitve van Windows oldalon,
- a server streamable-http modban elindithato,
- az LM Studio az mcp.json kiegeszites utan elerhetonek latja az Excel MCP-t,
- az LM Studio sajat chat feluleten olvasasi jellegu tesztpromptokkal korrekt valaszokat ad Excel fajlbol,
- a tesztek alapjan Excel telepites nelkul is mukodik az olvasasi/informaciokinyeresi hasznalat,
- az app Adatbazis modja mar index-alapu: a modell elso lepeskent a `00-INDEX.xlsx` adatforras-indexet hasznalja.

Fontos gyakorlati megfigyeles:

- a generic raw Excel read tul nagy es tul zajos cellaszintu JSON-t adhat vissza nagyobb tartomanyokra,
- az Adatbazis mod app-oldali szerzodese ezert nem nyers celladumpra, hanem indexelt adatforras-valasztasra es tomor, read-only informaciokinyeresre epul,
- a tool nem kepes onalloan fajlokat listazni a sandbox konyvtarbol,
- a `00-INDEX.xlsx` konvencio ezt a hianyt hidalja at az app szempontjabol.

Kovetkezmeny az app-integraciora:

- a felhasznalonak nem kell fajlnevet vagy munkalapnevet megadnia, ha a `00-INDEX.xlsx` alapjan a kerdeshez egyertelmuen valaszthato adatforras,
- az app elso koreben nem ad file picker UI-t,
- az app elso koreben nem probal fajllistat szerezni,
- ha az index alapjan sem dontheto el, melyik adatforrast kell hasznalni, a modell kerjen pontositas.

## Valasztott MCP server

Elso korben javasolt es elfogadott server:

- haris-musa/excel-mcp-server

Indoklas:

- Python alapu, ami jobban illeszkedik a jelenlegi backend okoszisztemahoz,
- nagyobb adoption es lathato kozossegi hasznalat,
- openpyxl alapu mukodes, nem igenyel Microsoft Excelt,
- szelesebb Excel muveleti keszlet, amelybol most csak vekony szeletet hasznalunk,
- tamogat stdio es HTTP jellegu transportokat,
- HTTP modban fajlutvonal-korlatozasi lehetoseg is elerheto EXCEL_FILES_PATH jellegu beallitassal.

A negokaz/excel-mcp-server jelenleg tartalek/opcionalis alternativa. Elonye az egyszeruseg es nehany Windows/live editing kepesseg, de az elso MVP celhoz a haris-musa valtozat szimpatikusabb.

## Hatarok

Az Excel/Adatbazis mod celja:

- LM Studio requestben engedelyezni az Excel MCP integraciot,
- a modellnek Excel-tabla-alapu valaszadasi szabalyokat adni,
- a user altal irt promptot tisztan menteni,
- a tool promptot csak provider request contextkent hasznalni,
- a normal chat, reasoning es streaming mukodest megtartani,
- olvasasi/informaciokinyeresi MVP-t adni Excel fajlok felett.

Nem cel elso korben:

- altalanos Excel szerkeszto asszisztens,
- chart/pivot/formatting workflow,
- workbook generalas felhasznaloi termekfunkciokent,
- kezi Excel fajlkezelo UI,
- sajat Excel parser vagy indexelo backend,
- RAG pipeline,
- embedding vagy Qdrant,
- Obsidian/Tudasbazis es Excel/Adatbazis egyideju hasznalata,
- tool-call debug UI,
- raw MCP/tool-call intermediate adatok mentese,
- Excel tartalom DB-be masolasa.

A server tobbet tudhat ezeknel, de az elso termekfelulet tudatosan szuk marad.

## Elofeltetelek

Az Excel/Adatbazis tool mode akkor tekintheto hasznalhatonak, ha:

- LM Studio 0.4.0 vagy ujabb fut,
- az LM Studio server settingsben engedelyezett az mcp.json szerverek API-bol torteno hivasa,
- ha az LM Studio API authentication aktiv, a backend .env-ben be van allitva az AI_ASSISTANT_LM_STUDIO_API_TOKEN,
- a haris-musa/excel-mcp-server mukodik az LM Studio sajat chat feluleten,
- az app backend configja ismeri az Excel integration id-t,
- az Excel fajlok kontrollalt, ismert lokalis konyvtarban vannak,
- a felhasznalo tudja, hogy a keresett informacio az Adatbazis modhoz tartozo Excel fajlokban talalhato,
- a kontrollalt Excel konyvtarban elerheto a `00-INDEX.xlsx` adatforras-index,
- a `00-INDEX.xlsx` eleg informaciot ad a relevans fajl/munkalap/tartomany/oszlop kivalasztasahoz.

Javasolt backend config:

    AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID=mcp/excel

Ha LM Studio authentication aktiv, szukseges lokalis backend config:

    AI_ASSISTANT_LM_STUDIO_API_TOKEN=<local-lm-studio-api-token>

Az Excel MCP server oldalan javasolt fajlkorlatozas:

    EXCEL_FILES_PATH=<controlled-local-excel-folder>

## Javasolt futtatasi mod az MVP-hez

Az elso MVP-hez a javasolt futtatasi mod:

    streamable-http

Indoklas:

- HTTP/SSE modban a server EXCEL_FILES_PATH sandboxot hasznal,
- a tool filepath ertekei ilyenkor csak relativ utak lehetnek az EXCEL_FILES_PATH alatt,
- abszolut utak es directory traversal probalkozasok elutasitasra kerulnek,
- ez jobban illik az Adatbazis mod kontrollalt lokalis adatforras szemleletehez.

Javasolt inditasi alapelv:

    EXCEL_FILES_PATH=<controlled-local-excel-folder>
    FASTMCP_HOST=127.0.0.1
    FASTMCP_PORT=8017
    excel-mcp-server streamable-http

Az MVP-ben a stdio modot ne hasznaljuk elsodleges integraciokent.

Indoklas:

- stdio modban a server abszolut fajlutakat fogad a kliens/tool hivasbol,
- ez kevesbe jol korlatozhato termekoldali adatforras-modellhez,
- az Adatbazis mod celja nem tetszoleges file access, hanem kontrollalt Excel adatforras konyvtar.

## Termekviselkedes

Ha a felhasznalo bekapcsolja az Adatbazis gombot:

- a frontend tool_mode erteke excel/adatbazis jellegu modra valt,
- a backend az Excel tool policy-t valasztja,
- az LM Studio provider request megkapja az Excel integration id-t,
- a provider request system contextje megkapja az Excel prompt policy blokkot,
- a user uzenet tartalma valtozatlanul, csak a user altal irt szoveggel kerul mentesre.

Ha az Adatbazis gomb nincs bekapcsolva:

- nem megy Excel integration,
- nem kerul Excel prompt blokk a requestbe,
- a normal chat viselkedes valtozatlan marad.

Ha a Tudasbazis mod aktiv:

- az Adatbazis mod nem lehet aktiv,
- az Obsidian integration/policy hasznalodik,
- Excel integration nem kerul a requestbe.

Ha az Adatbazis mod aktiv:

- a Tudasbazis mod nem lehet aktiv,
- Excel integration/policy hasznalodik,
- Obsidian integration nem kerul a requestbe.

A Gondolkodo mod tovabbra is kombinalhato az Adatbazis moddal.

## Prompt policy

Az Excel prompt policy legyen szigoru, rovid, index-router alapu es olvasasi/informaciokinyeresi iranyu. A jelenlegi elfogadott valtozat szandekosan 9B-barátabb: kevesebb ismetles, egyertelmu fajlnev-utalas flow, egyetlen Toolhasználat blokk es celzott read-only toolvalasztas. Domain-specifikus mechanikus keresesi szabalyokat nem tartalmaz.

Adatbazis modban a modell feladata nem altalanos vilagtudasbol valaszolni, hanem a konfiguralt Excel fajlok/munkalapok tartalma alapjan dolgozni.

Aktualis policy lenyege:

```text
[Excel adatbázis mód]

Szerep:
Te egy lokális LLM vagy, amely Excel fájlokban tárolt táblázatos adatokkal dolgozik mcp/excel eszközön keresztül.
A felhasználó kérdésére kizárólag a rendelkezésre álló Excel fájlok kiolvasott tartalma alapján válaszolhatsz.

Alap flow:
1. Először mindig olvasd el a 00-INDEX.xlsx fájlt.
2. A 00-INDEX.xlsx nem válaszforrás, hanem útválasztó index.
3. Az indexből válaszd ki a megfelelő fájlt, munkalapot, tartományt, oszlopokat és read-only MCP eszközt.
4. A tényleges választ mindig a kiválasztott forrás Excel fájlból nyerd ki.

Fájlnév-utalás:
- Ha a felhasználó fájlnévre vagy fájlnévrészletre utal, először keresd meg ezt a 00-INDEX.xlsx fájllistájában.
- Ha pontosan egy fájl egyértelműen azonosítható, kizárólag abban a fájlban keress és válaszolj.
- Ha nincs egyértelmű fájltalálat, fogadd el, ne ragadj le ezen, hanem a feltett kérdés és a 00-INDEX.xlsx tartalma alapján próbáld kiválasztani a legjobb adatforrást, kizárólag abban a fájlban keress és válaszolj.
- Ha így sem dönthető el megbízhatóan, fogadd el és kérj pontosítást majd állj le.

Toolhasználat:
- A 00-INDEX.xlsx elolvasása után válassz egy elsődleges fájlt és munkalapot, majd a kérdéshez illő célzott eszközt használd.
- Oszlopok felsorolásához: list_excel_columns.
- Sheet szerkezetének vagy oszlopmintáinak megértéséhez: describe_excel_sheet.
- Konkrét rekord kereséséhez azonosító, név, kód vagy ismert mezőérték alapján: lookup_excel_rows.
- Részszöveges kereséshez szöveges oszlopban: lookup_excel_rows match_mode="contains".
- Több sor listázásához oszlopérték alapján: filter_excel_rows.
- Azonos értékű kapcsolódó sorok kereséséhez egy forrássor alapján: find_excel_rows_with_same_value.
- Összesítéshez, rangsorhoz, darabszámhoz, minimumhoz, maximumhoz, átlaghoz vagy összeghez: aggregate_excel_data.
- read_data_from_excel csak indexlap, kis tartomány vagy célzott ellenőrzés esetén használható. Nagy forrástáblát ne dumpolj és ne kézzel böngéssz végig.
- Ha egy célzott eszköz megbízható találatot ad, válaszolj abból. Ha célzott kereséssel sem dönthető el megbízhatóan, kérj pontosítást és állj le.

Szigorú szabályok:
- Tilos hallucinálni.
- A korábbi assistant válaszok nem forrásadatok, csak beszélgetési előzmények.
- Ha a felhasználó rákérdez vagy vitatja a korábbi választ, ellenőrizd újra a kiválasztott Excel forrásból, és a forrásadat alapján javítsd magad.
- Tilos olyan adatot, számot, dátumot, nevet vagy következtetést adni, amelyet a kiolvasott Excel adatok nem támasztanak alá.
- Ha nem tudsz megbízható választ adni, fogadd el. Ne találgass és ne erőlködj, mondd ki röviden, hogy mi hiányzik, és kérj pontosítást, majd állj le.
- Ha egy helyen egyértelműen megtaláltad a keresett választ, azonnal válaszolj. Ne kezdj el keresni máshol is.
- Kizárólag olvasási és információkinyerési műveleteket használhatsz.
- Tilos Excel fájlt létrehozni, módosítani, törölni, formázni, képletet írni, munkalapot átnevezni, új munkalapot létrehozni, pivot táblát, diagramot vagy segéd-összefoglalót készíteni.
- A tiltások akkor is érvényesek, ha a felhasználó erre kér.

Válasz:
- Magyarul, tömören és jól strukturáltan válaszolj.
- Ha számítást, összesítést vagy szűrést végzel, röviden jelezd, melyik fájl, munkalap és oszlopok alapján dolgoztál.
```


Megjegyzes:

- az app repo csak az app oldali prompt/policy szerzodest rogziti,
- az Excel MCP szerver belso read-only tool bovitesenek reszletei kulon projektben/munkamenetben elnek,
- az app szempontjabol a lenyeg az, hogy az Adatbazis mod tomor, read-only informaciokinyeresre terelje a modellt, a korabbi assistant valaszokat pedig ne tekintse forrasadatnak.

### Szigorusagi dontes

Az Adatbazis mod legyen tenylegesen Excel-data-grounded mod.

Indoklas:

- normal chat mod mar letezik altalanos valaszadasra,
- Adatbazis mod bekapcsolasa explicit felhasznaloi jelzes,
- a user ilyenkor azt varja, hogy a valasz a tablazatos adatforrasbol jojjon,
- ha nincs adat vagy nem talalhato relevans workbook/sheet, jobb ezt kimondani, mint kitalalni.

## Prompt composition

A user prompt nem modosulhat a DB-ben.

Helyes modell:

    stored user message:
      content = amit a user beirt

    provider request:
      assistant system prompt
      + Excel tool prompt blokk
      + chat history
      + current user content

Invarians:

    Excel instructions are request context, not stored user text.

Kovetkezmenyek:

- a UI-ban a user csak a sajat kerdeset latja,
- a mentett beszelgetes nem telik meg belso tool instrukciokkal,
- a tool policy kesobb modosithato regi user uzenetek atirasa nelkul,
- a context guard tovabbra is a normal chat contentre epul.

Fontos implementacios dontes:

- ne toldjuk meg a user promptot Excel instrukciokkal,
- ne kelljen a mentesnel belso instrukciokat levagni,
- minden Excel read-only es grounding szabaly a backend altal osszeallitott system/request contextben jelenjen meg.

## Backend policy

A tool_modes registry kovetkezo konkret modja legyen az Excel/Adatbazis mod.

Javasolt internal id:

    excel

Javasolt user-facing label:

    Adatbazis

Javasolt policy:

    id: excel
    label: Adatbazis
    integration_ids: [settings.lm_studio_excel_integration_id]
    prompt_instructions: EXCEL_TOOL_PROMPT

A none policy maradjon ures.

Az obsidian policy maradjon valtozatlan.

## LM Studio integration

Az LM Studio mcp.json szerver neve az elfogadott tesztkonfiguracio szerint:

    excel

Ezert a provider oldali integration id elso korben:

    mcp/excel

Az app backendje ne probalja kozvetlenul hivni az Excel MCP servert. Az elso integracios korben a felelossegi korok:

- Excel MCP server: Excel fajlok olvasasa MCP toolokon keresztul,
- LM Studio: MCP serverek es model tool use osszekotese,
- AI Assistant backend: tool mode valasztas, system prompt policy, integrations payload,
- frontend: user-facing tool mode kapcsolok.

Ha kesobb kiderul, hogy az LM Studio UI-ban kapcsolhato tool engedelyek API hivasokra is megbizhatoan hatnak, azt kulon lehet dokumentalni. Az MVP implementacio nem epul erre. A read-only korlat elsodleges es kotelezo retege a backend system prompt policy.

## Frontend UI

Az elso UI valtozat minimalis legyen es kovesse a jelenlegi tool mode sort.

Composer mode sor:

- Gondolkodo,
- Tudasbazis,
- Adatbazis.

Viselkedes:

- Gondolkodo onallo toggle, kombinalhato barmelyik tool mode-dal,
- Tudasbazis es Adatbazis egymast kizaro tool mode-ok,
- ha Tudasbazis aktiv es a user Adatbazisra kattint, Tudasbazis kikapcsol es Adatbazis bekapcsol,
- ha Adatbazis aktiv es a user Tudasbazisra kattint, Adatbazis kikapcsol es Tudasbazis bekapcsol,
- aktiv tool mode ujrakattintasa kikapcsolja azt es visszaall normal modra.

Tooltip javaslat:

- inaktiv: Adatbazisbol torteno valaszadas mod kikapcsolva.
- aktiv: Adatbazisbol torteno valaszadas mod bekapcsolva.

A felhasznaloi UI ne emlitse, hogy MCP, integration id vagy konkret server fut a hatterben.

### UX megjegyzes

Az elso verzioban a gomb csak modvalaszto. Nem fajlvalaszto.

Ennek megfeleloen a felhasznalonak nem kell file pickerrel vagy fajlnevvel kezdenie, ha a kerdes a `00-INDEX.xlsx` alapjan egyertelmuen adatforrashoz kotheto.

Pelda:

    Melyik orszagban volt a legnagyobb profit?

Helyes viselkedes:

- a modell eloszor az indexet olvassa,
- abbol valasztja ki a relevans Excel fajlt es munkalapot,
- utana csak a szukseges adatokat/osszefoglalast keri le,
- ha az index alapjan sem egyertelmu az adatforras, pontositas ker.

## Elso MVP smoke tesztek

Manual smoke minimum:

1. LM Studio sajat chat feluleten az Excel MCP server mukodik.
2. Az app normal chat modban nem kuld Excel integrationt.
3. Adatbazis modban a provider request tartalmazza az Excel integration id-t.
4. Adatbazis modban a system prompt tartalmazza az Excel prompt policy-t.
5. A user prompt tisztan mentodik, belso Excel policy nelkul.
6. A user egyszeru kerdest tesz fel egy ismert workbook ismert adatara, es a modell az Excel fajl alapjan valaszol.
7. Ha a user nem ad fajlnevet vagy az adatforras nem egyertelmu, a modell pontositas ker.
8. Ha nincs relevans adat, a modell ezt vilagosan kimondja.
9. Ha a user irasi/modosito muveletre ker, a modell nem hiv irasi toolt, hanem jelzi, hogy az Adatbazis mod olvasasi mod.
10. Tudasbazis es Adatbazis egyszerre nem lehet aktiv.
11. Gondolkodo + Adatbazis egyszerre mukodik.
12. Stream, stop, retry es regenerate flow nem romlik.

## Kockazatok es nyitott kerdesek

### Fajlterulet es jogosultsag

A legfontosabb gyakorlati kerdes, hogy az Excel MCP server milyen konyvtarat lat.

Javaslat:

- legyen egy kontrollalt lokalis Excel adatforras konyvtar,
- ne engedjunk tetszoleges abszolut fajlutakat termekviselkedeskent,
- az EXCEL_FILES_PATH vagy ennek megfelelo server-oldali korlatozas legyen beallitva.

### Olvasas vs iras

Az elso MVP olvasasi/informaciokinyeresi mod.

Kesobb lehet kulon irasi/szerkesztesi modot tervezni, de ne keverjuk az elso Adatbazis modba.

Az LM Studio feluleten lathato tool kapcsolok hasznosak lehetnek, de az MVP nem tekinti oket garancialis kontrollnak, amig nincs kulon igazolva, hogy az API hivasokra is azonosan ervenyesulnek.

Ezert a backend system promptban minden Adatbazis requestnel explicit szerepelnie kell:

- csak olvasasi muvelet,
- iras/modositas/formazas/torles tilos,
- user prompt sem oldhatja fel ezt a tiltast.

### Workbook discovery

A gyakorlati teszt alapjan a valasztott MCP server nem tud egyszeruen fajllistat adni a sandbox konyvtarbol.

Aktualis MVP dontes:

- nem epitunk automatikus workbook discoveryt,
- nem epitunk file picker UI-t,
- a discovery konvencio a kontrollalt Excel konyvtarban levo `00-INDEX.xlsx`,
- a modell elso lepeskent ezt az index workbookot olvassa,
- ha az index sem ad eleg informaciot a helyes adatforras kivalasztasahoz, a modell kerjen pontositas.

Kesobb lehet kulon konvencio:

- backend configbol ismert Excel fajllista,
- frontend file picker,
- index workbook generalo/validalo workflow.

### Tartalmi pontossag

A modell ne hasznalja az Excel modot altalanos talalgatasra.

Ha az adat nem talalhato vagy nem egyertelmu, a helyes valasz az, hogy a tablazatos adatforras alapjan nem megvalaszolhato.

## Elso implementacios javaslat

1. Excel integration id config hozzaadasa backend settingshez.
2. tool_modes registry bovites excel/Adatbazis policy-val.
3. frontend AssistantToolMode tipus bovites excel ertekkel.
4. ComposerModeBar Adatbazis gomb hozzaadasa a jelenlegi style es tooltip mintaval.
5. Composer tool mode logika bovitese ugy, hogy Tudasbazis es Adatbazis egymast kizarja.
6. provider request integrations ellenorzese stream es non-stream uton.
7. Excel system prompt policy hozzaadasa ugy, hogy a user prompt tisztan marad.
8. backend tesztek: policy, integrations, user content tisztasag, obsidian/excel kolcsonos kizaras.
9. frontend build es manual UI smoke.
10. manual smoke LM Studio + Excel MCP serverrel.

## Status

Status: MVP implementacio kesz, roviditett index-router Adatbazis prompttal es felhasznaloi proban mukodokepes Excel kerdes-valasz flow-val stabilnak itelve.

Kesz:

- Excel integration id config: `AI_ASSISTANT_LM_STUDIO_EXCEL_INTEGRATION_ID`, default `mcp/excel`,
- backend `tool_modes.py` `excel` policy roviditett index-router, read-only system prompttal,
- schemas/API es frontend type `tool_mode: "excel"` ertekkel,
- ComposerModeBar `Adatbázis` gomb,
- Tudásbázis es Adatbázis egymast kizaro tool mode-kent mukodik,
- user prompt tisztan mentodik,
- backend tool mode tesztek bovultek Excel policy/integration/user-content invariansokra,
- frontend build sikeres,
- manual smoke: Excel MCP elerheto LM Studio felol es az app stabilan valaszol,
- manual smoke: `00-INDEX.xlsx` alapjan a modell megtalalta a relevans `minta.xlsx`/`Sheet1` adatforrast es osszesitett profit kerdesre helyes, tomor valaszt adott,
- app oldali prompt tiltja a pivot/diagram/uj munkalap/seged-osszefoglalo letrehozast es minden Excel irasi/mutacios muveletet,
- app oldali prompt fajlnev-utalas eseten eloszor egyertelmu index-talalatot keres, talalat hianyaban pedig az index alapjan valaszt adatforrast,
- app oldali prompt celzott read-only toolvalasztast rogzit: oszloplista, schema, lookup, filter, same-value es aggregate eszkozokkel.

Tovabbra is parkolopalyan marad:

- file picker UI,
- automatikus workbook discovery,
- read-only wrapper MCP server,
- Excel irasi/szerkesztesi mod.

## Parkolopalyan

- Excel fajl feltoltes vagy file picker UI,
- workbook lista UI,
- sheet preview UI,
- chart/pivot/formazas workflow,
- Excel irasi/szerkesztesi mod,
- Excel tool-call debug panel,
- tobb tool mode egyideju hasznalata,
- Obsidian + Excel egy kozos valaszban.
