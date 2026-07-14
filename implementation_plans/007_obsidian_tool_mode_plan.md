# 007 - Obsidian Tool Mode Plan

## Cel

Ez a dokumentum az elso konkret tool mode, az Obsidian MCP integracio implementacios terve.

A terv a kovetkezo dokumentumokra epul:

- `005_mcp_tool_modes_direction.md` - magas szintu MCP/tool mode alapvetesek,
- `006_tool_mode_foundation_plan.md` - kozos backend/frontend tool mode foundation.

Ez a dokumentum nem altalanos MCP terv, nem plugin manager terv, es nem Excel vagy mas kesobbi eszkozmod terve. Kizarolag azt rogziti, hogy az `obsidian` tool mode hogyan viselkedjen.

## Hatarok

Az Obsidian mod celja:

- LM Studio requestben engedelyezni az Obsidian MCP integraciot,
- a modellnek Obsidian vault-alapu valaszadasi szabalyokat adni,
- a user altal irt promptot tisztan menteni,
- a tool promptot csak provider request contextkent hasznalni,
- a normal chat, reasoning es streaming mukodest megtartani.

Nem cel:

- sajat vault indexeles,
- RAG pipeline,
- embedding vagy Qdrant,
- forrashivatkozas workflow,
- Obsidian note-ok DB-be masolasa,
- generic MCP server manager,
- tobb tool egyszerre,
- tool-call debug UI az elso korben.

## Elofeltetelek

Az Obsidian tool mode akkor tekintheto hasznalhatonak, ha:

- LM Studio 0.4.0 vagy ujabb fut,
- az Obsidian MCP server mukodik az LM Studio sajat chat feluleten,
- az LM Studio server settingsben engedelyezett az mcp.json szerverek API-bol torteno hivasa,
- ha az LM Studio API authentication aktiv, a backend `.env`-ben be van allitva az `AI_ASSISTANT_LM_STUDIO_API_TOKEN`,
- az app backend configja ismeri az Obsidian integration id-t,
- a vaultban letezik es karban van tartva a `00-INDEX.md`,
- a `00-INDEX.md` tenylegesen hasznalhato belepesi pont a vault tartalmahoz.

Javasolt backend config:

    AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian

Ha LM Studio authentication aktiv, szukseges lokalis backend config:

    AI_ASSISTANT_LM_STUDIO_API_TOKEN=<local-lm-studio-api-token>

Alapertelmezett Obsidian integration id:

    mcp/obsidian

## Termekviselkedes

Ha a felhasznalo bekapcsolja az Obsidian gombot:

- a frontend `tool_mode: "obsidian"` erteket kuld,
- a backend az Obsidian tool policy-t valasztja,
- az LM Studio provider request megkapja az Obsidian integration id-t,
- a provider request system contextje megkapja az Obsidian prompt policy blokkot,
- a user uzenet tartalma valtozatlanul, csak a user altal irt szoveggel kerul mentesre.

Ha az Obsidian gomb nincs bekapcsolva:

- a `tool_mode` `none`,
- nem megy Obsidian integration,
- nem kerul Obsidian prompt blokk a requestbe,
- a normal chat viselkedes valtozatlan marad.

## Prompt policy

Az Obsidian/Tudásbázis prompt policy legyen szigoru, de ne legyen bonyolultabb az Excel/Adatbázis promptnal.

Tudásbázis modban a modell feladata nem altalanos vilagtudasbol vagy Obsidian/MCP eszkoztudasbol valaszolni, hanem a vault kiolvasott jegyzetei alapjan dolgozni.

Aktualis elfogadott policy lenyege:

- fejlec: `[Tudásbázis mód]`,
- a modell lokalis LLM-kent Obsidian vaultban tarolt tudásanyaggal dolgozik MCP eszkozon keresztul,
- a felhasznalo kerdesere kizarolag a vaultbol kiolvasott jegyzetek tartalma alapjan valaszolhat,
- Tudásbázis modban mindig hasznalnia kell az Obsidian MCP eszkozoket,
- elso lepes mindig a `00-INDEX.md` olvasasa,
- a `00-INDEX.md` csak utvalaszto index, nem vegso valaszforras,
- az index alapjan kell kivalasztani a relevans jegyzeteket,
- a tenyleges valaszt a kivalasztott jegyzetek kiolvasott tartalmabol kell megadni,
- tilos hallucinalni vagy vault-jegyzetekkel ala nem tamasztott funkciot, leirast vagy kovetkeztetest adni,
- ha nincs megbizhato valasz, a modell mondja ki roviden, mi hianyzik, es kerjen pontosítast,
- tilos altalanos Obsidian vagy MCP funkciomagyarazatot adni vault-evidence helyett,
- csak olvasasi es informaciokinyeresi muveletek engedelyezettek,
- tilos jegyzetet letrehozni, modositani, torolni, atnevezni vagy athelyezni,
- a valasz magyar, tomor es jol strukturalt legyen.

Ez a prompt 2026-07-14-en finomitva lett, mert reasoning nelkul a modell hajlamos volt altalanos Obsidian/MCP valaszt adni app-dokumentacios kerdesekre. Az uj policy celja, hogy a modell a `00-INDEX.md` + relevans jegyzet flow-ra legyen kenyszeritve gondolkodo mod nelkul is.

### Szigorusagi dontes

Az Obsidian mod legyen tenylegesen vault-only mod.

Indoklas:

- normal chat mod mar letezik altalanos valaszadasra,
- Obsidian mod bekapcsolasa explicit felhasznaloi jelzes,
- a user ilyenkor azt varja, hogy a valasz a sajat vaultbol jojjon,
- ha nincs vault evidence, az jobb, ha kiderul, mintha a modell kitalalna valamit.

## Prompt composition

A user prompt nem modosulhat a DB-ben.

Helyes modell:

    stored user message:
      content = amit a user beirt

    provider request:
      assistant system prompt
      + Obsidian tool prompt blokk
      + chat history
      + current user content

A jelenlegi provider a system role uzenetekbol `system_prompt` mezot epit. Ezert az Obsidian policy-t a system contexthez erdemes hozzaadni, nem a user content ele vagy vegehez.

### Invarians

> Obsidian instructions are request context, not stored user text.

Kovetkezmenyek:

- a UI-ban a user csak a sajat kerdeset latja,
- a mentett beszelgetes nem telik meg belso tool instrukciokkal,
- a tool policy kesobb modosithato regi user uzenetek atirasa nelkul,
- a context guard tovabbra is a normal chat contentre epul.

## Backend policy

A `tool_modes` registry Obsidian policy-ja bovuljon:

    id: "obsidian"
    label: "Obsidian"
    integration_ids: [settings.lm_studio_obsidian_integration_id]
    prompt_instructions: OBSIDIAN_TOOL_PROMPT

A `none` policy maradjon ures:

    integration_ids: []
    prompt_instructions: None

## Context builder

A service reteg jelenleg LLMChatMessage listat epit.

Obsidian modnal a context buildernek tudnia kell:

- a normal system prompt megtartasat,
- az Obsidian prompt blokk hozzaadasat,
- a user/assistant history valtozatlan atadasat.

Javasolt helper:

    _to_llm_messages(settings, messages, tool_prompt=None)

Vagy:

    _build_llm_messages(settings, messages, tool_policy)

MVP-ben a kisebb modositas eleg:

- `PreparedAssistantStream` kapja meg a policy promptot mar beillesztett messages listaban,
- non-stream `_complete_chat` ugyanazt a helper logikat hasznalja,
- `none` modban a helper pontosan ugyanazt az outputot adja, mint eddig.

## Provider request

Obsidian modban az LM Studio provider requestben egyszerre kell megjelennie:

    integrations: ["mcp/obsidian"]
    system_prompt: "...normal system prompt...\n\n[Tudásbázis mód]\n..."

A provider oldali `integrations` tamogatas mar foundation szinten elindult. Az Obsidian terv fo providerhez kapcsolodo elvarasa az, hogy:

- stream es non-stream ugyanazt az integrations + system_prompt szerzodest hasznalja,
- `none` modban ne jelenjen meg `integrations`,
- Obsidian modban jelenjen meg a configolt integration id.

## Hibakezeles

Ket hibatipust kulon kell kezelni.

### Technikai hiba

Ilyen, ha:

- az LM Studio nem ismeri vagy nem fogadja el az `integrations` mezot,
- az mcp.json API-bol torteno hasznalata nincs engedelyezve,
- az Obsidian MCP server nem fut vagy nem erheto el,
- az integration id rossz,
- tool-call kozben provider error jon.

Javasolt UI/API szovegek:

    Az Obsidian eszkozmod nincs beallitva.
    Az LM Studio nem engedelyezi az mcp.json szerverek API-bol torteno hivasat.
    Az Obsidian MCP szerver nem erheto el.
    Az Obsidian integracio hivas kozben hibat adott.

MVP-ben ezek valoszinuleg provider error formaban erkeznek, es a meglevo error/notice rendszer jeleniti meg oket.

### Tartalmi hiany

Ilyen, ha:

- a `00-INDEX.md` nem talalhato,
- a vaultban nincs relevans jegyzet,
- a relevans jegyzetek alapjan nem valaszolhato meg a kerdes.

Ezek nem app hibak. Ilyenkor a modell vegso valaszban mondja ki vilagosan, hogy a vault alapjan nem tud valaszolni.

## UI viselkedes

Az elso Obsidian implementacio UI szinten minimalis marad.

Mar adott:

- Obsidian gomb a composer mode sorban,
- aktiv/inaktiv allapot,
- egyszerre egy tool mode,
- reasoning fuggetlenul kapcsolhato.

Elso korben nem kell:

- tool-call viewer,
- kulon vault keresesi animacio,
- raw MCP output,
- forrasfajl lista UI.

Kesobbi finomitas lehet:

- "Obsidian mod aktiv" jellegu finom notice,
- tool-call aktivitasi sor,
- talalt note/fajl nevek megjelenitese, ha az MCP outputbol megbizhatoan kinyerheto.

## Mentes es kontextus

MVP-ben:

- user content tisztan mentodik,
- assistant final content normal modon mentodik,
- raw tool-call output nem mentodik,
- Tudásbázis prompt wrapper nem mentodik user uzenetkent,
- MCP intermediate lepesek nem kerulnek vissza kovetkezo prompt history-ba.

Nyitott, de kesobb hasznos lehet:

    message_metadata.tool_mode = "obsidian"

Ez visszanezeshez jo lehet, de nem feltetele az elso Obsidian mukodesnek.

## Tesztelesi terv

### Backend unit tesztek

- Obsidian policy tartalmazza a configolt integration id-t.
- Obsidian policy tartalmaz prompt instruction blokkot.
- `none` policy nem tartalmaz integrationt es prompt blokkot.
- ismeretlen tool mode tovabbra is validacios hibat ad.

### Service/context tesztek

- Obsidian modban a provider messages system promptja tartalmazza az Obsidian policy blokkot.
- Obsidian modban a provider megkapja az integrations listat.
- A mentett user message content pontosan a user altal irt szoveg marad.
- `none` modban a provider messages nem tartalmaz Obsidian blokkot.
- Regenerate es retry stream ugyanazt a tool policy-t at tudja adni.

### Provider payload tesztek

- Obsidian modban a native payload tartalmazza:

        integrations: ["mcp/obsidian"]

- A native payload `system_prompt` mezoje tartalmazza az Obsidian policy-t.
- Stream payloadban ugyanez ervenyes.

### Manual smoke

Elokeszites:

1. LM Studio sajat chat feluleten Obsidian MCP mukodik.
2. Ugyanaz a modell be van toltve vagy betoltheto.
3. Backend config:

        AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian

4. Ha LM Studio authentication aktiv, a backend `.env` tartalmazza az `AI_ASSISTANT_LM_STUDIO_API_TOKEN` erteket.
5. Az app elinditva a stabil start scripttel.

Smoke 1 - normal mod:

    Obsidian gomb kikapcsolva.
    Prompt: Dobj ossze egy atfogo Linux privilege escalation cheat-sheet-et.

Elfogadhato eredmeny:

- a modell nem latja a vaultot,
- vagy altalanos tudasa szerint valaszol,
- vagy azt mondja, hogy nincs hozzaferese a vault tartalmahoz.

Smoke 2 - Obsidian mod:

    Obsidian gomb bekapcsolva.
    Ugyanaz a prompt.

Elvart eredmeny:

- a modell nem mondja azt, hogy nincs hozzaferese a vaulthoz,
- hasznalja az Obsidian MCP integraciot,
- a `00-INDEX.md` alapjan keresi a relevans jegyzeteket,
- vault-alapu, strukturalt magyar valaszt ad.

Smoke 3 - hianyzo tartalom:

    Obsidian gomb bekapcsolva.
    Olyan kerdes, amelyrol biztosan nincs info a vaultban.

Elvart eredmeny:

- a modell vilagosan jelzi, hogy a vault alapjan nem tud valaszolni,
- nem talal ki kulso informaciot.

## Implementacios lepesek

1. Obsidian prompt policy konstans letrehozasa backendben.
2. `ToolModePolicy` Obsidian prompt_instructions mezon keresztuli bovitese.
3. Context/message builder bovitese opcionalis tool prompttal.
4. Send non-stream utvonal Obsidian prompt context bekotese.
5. Send stream utvonal Obsidian prompt context bekotese.
6. Regenerate es retry stream utvonalak tool prompt context bekotese.
7. Backend tesztek policy-re, contextre es user content tisztasagra.
8. Provider tesztek integrations + system_prompt egyuttes jelenletere.
9. Frontend build ellenorzes, UI modositas nelkul vagy minimalis finomitassal.
10. LM Studio API authentication tamogatas dokumentalasa es `.env.example` ures token kulcs.
11. Manual smoke LM Studio Obsidian MCP konfiguracioval.
12. Allapotfajlok frissitese, ha az implementacio elkeszult.

## Nyitott dontesek

- Mentsuk-e az MVP-ben uzenetszinten a `tool_mode` metadata-t, vagy halasszuk kesobbre?
- Kell-e kulon UI notice, amikor Obsidian mod aktiv, vagy eleg az aktiv gomb?
- Kell-e kesobb forrasfajl/nevek megjelenitese, ha az MCP output ezt ertelmesen adja?
- A regenerate alapbol a jelenlegi aktiv tool mode szerint fusson, vagy kesobb az eredeti uzenet tool mode-ja szerint?

## Dontesi osszefoglalo

- Obsidian mod legyen szigoru vault-only mod.
- A user prompt ne modosuljon es ne szennyezodjon belso instrukcioval.
- Az Obsidian prompt policy a provider request system contextjebe keruljon.
- Az LM Studio request Obsidian modban kapja meg a configolt MCP integration id-t.
- Raw MCP/tool-call intermediate adat elso korben ne legyen mentve es ne keruljon vissza chat kontextusba.
- UI szinten az elso korben eleg az aktiv Obsidian gomb es a meglevo error/notice rendszer.
