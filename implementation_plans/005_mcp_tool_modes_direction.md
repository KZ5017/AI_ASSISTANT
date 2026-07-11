# 005 - MCP Tool Modes Direction

## Cel

Ez a dokumentum nem implementacios terv, hanem iranykijelolo alapvetes az LM Studio MCP integraciohoz.

A cel az, hogy a standalone AI Assistant kesobb tudjon nehany, elore ismert eszkozmoddal dolgozni, peldaul Obsidian MCP-vel, ugy, hogy kozben:

- az alkalmazas tovabbra is altalanos lokalis chat app marad,
- nem valik generic MCP marketplace-e vagy plugin managerre,
- a felhasznalo egyszeru termeszetes kerdest irhasson,
- a backend intezze az adott eszkozmodhoz tartozo prompt-kornyezetet es LM Studio integracio bekoteset,
- a reasoning mod es az eszkozmodok egymastol fuggetlenul mukodjenek.

## Kiindulo megfigyeles

Az LM Studio sajat chat feluleten az mcp.json-ban beallitott eszkozok egy egyszeru kapcsoloval bekapcsolhatok. Ha ott az Obsidian MCP aktiv, akkor a modell kepes a vault tartalma alapjan valaszolni.

A sajat webes feluletunkon ugyanaz a prompt jelenleg nem latja a vaultot, mert az LM Studio feluleten bekapcsolt eszkozhasznalat nem globalis allapot, amit minden kulso API hivas automatikusan orokol.

Az API hivasnal explicit modon kell jelezni az LM Studio fele, hogy melyik MCP integracio legyen elerheto az adott kereseshez.

## Termekdontes

Ne nyers "MCP szerverekben" gondolkodjunk a UI es a chat viselkedes szintjen, hanem magasabb szintu eszkozmodokban.

Javasolt mentalis modell:

    reasoningEnabled: boolean
    activeToolMode: "none" | "obsidian" | "excel" | ...

A reasoning kapcsolo egy kulon dimenzio:

- mukodhet normal chat mellett,
- mukodhet Obsidian mod mellett,
- mukodhet kesobbi Excel vagy mas eszkozmod mellett.

Az eszkozmod viszont egyszerre csak egy lehet aktiv:

- vagy nincs eszkozmod,
- vagy Obsidian,
- vagy kesobbi Excel,
- vagy egy masik konkret, elore tamogatott mod.

Ez azert fontos, mert az egyes eszkozmodok nem csak LM Studio integrations beallitast jelentenek, hanem sajat backend oldali viselkedest, prompt-kornyezetet es kesobb akar sajat UI-visszajelzest is.

## Nem cel

Ebben az iranyban tovabbra sem cel:

- generic MCP server manager epites,
- tetszoleges mcp.json szerverek dinamikus UI-listazasa,
- tobb tool egyideju aktiv hasznalata,
- BoberDetective-szeru RAG vagy dokumentum workflow,
- Obsidian tartalom sajat adatbazisba indexelese,
- Qdrant, embedding, source reference, provenance vagy audit reteg,
- tool-call lepesek teljes debug UI-ja az elso korben.

Az Obsidian MCP nem RAG modul lesz az appon belul, hanem LM Studio altal hivott kulso eszkoz, amelyet a backend adott kerdeshez explicit engedelyez.

Fontos LM Studio API-auth alapvetes: ha az LM Studio-ban engedelyezve van az API-bol torteno MCP/mcp.json eszkozhasznalat, az LM Studio authentication bekapcsolasat is kerheti. Ilyenkor az auth globalis: nem csak az MCP-s chat hivasok, hanem a modell-listazas, betoltes, levalasztas es normal chat hivasok is csak `Authorization: Bearer ...` fejleccel mukodnek. Ezert a backend provider szintjen kell opcionális API token tamogatas, nem az egyes tool mode-okban kulon. A token lokalis `.env` ertek, dokumentacioba es gitbe nem kerulhet be konkret ertekkel.

## Obsidian mod alapvetes

Az elso konkret eszkozmod varhatoan az Obsidian lesz.

A felhasznalo ne irjon hosszu rendszerutasitast. Peldaul ne neki kelljen ezt minden alkalommal megfogalmaznia:

    Te egy lokalis LLM vagy es egy Obsidian vaultban dolgozol.
    A kerdesre csak a vault tartalma alapjan valaszolhatsz.
    A vault tartalmat a 00-INDEX.md fajl fogja ossze.
    A 00-INDEX.md fajlt hasznald valasz helyenek felkutatasahoz.

Ehelyett a user csak a feladatot irja:

    Dobj ossze egy atfogo Linux privilege escalation cheat-sheet-et.

Obsidian modban a backend feladata lesz:

- az Obsidian MCP integracio bekapcsolasa az LM Studio requestben,
- a vault-alapu valaszadasi szabalyok hozzaadasa,
- a 00-INDEX.md hasznalatanak instrukciozasa,
- annak rogzitese a modell fele, hogy a valasz csak a vault tartalmara epulhet,
- a user prompt es az eszkozmodhoz tartozo belso prompt-kornyezet tiszta szetvalasztasa.

## Kesobbi eszkozmodok

Valoszinu, hogy kesobb lesz meg nehany tovabbi mod. A jelenlegi gondolkodas szerint ezek szama kicsi marad:

- Obsidian biztosan,
- Excel vagy tablazatos eszkozmod lehetseges,
- legfeljebb nehany tovabbi konkret eszkoz.

Ezert nem erdemes altalanos plugin rendszert epiteni. Jobb egy explicit, tipusos, keves modra optimalizalt szerkezet:

    "none"
    "obsidian"
    "excel"
    "..."

Minden mod sajat backend policy-t kaphat:

- milyen LM Studio integrations menjen a requestbe,
- milyen system/developer prompt-kornyezet jar hozza,
- milyen validaciok kellenek,
- milyen UI felirat vagy allapot jelenjen meg,
- milyen hibauzenet legyen, ha az adott eszkoz nem elerheto.

## Javasolt frontend irany

A composer jelenlegi logikaja bovulhet, de ne valjon zsufoltta.

Javasolt elrendezes:

- a chat beviteli mezo mellett kozvetlenul maradjon az elkuldes gomb,
- a beviteli mezo alatt jelenjen meg egy kompakt mod-sor,
- ebben a sorban legyen a Gondolkodo kapcsolo,
- mellette az Obsidian es kesobb mas eszkozmod kapcsolok,
- a gombok vizualisan ugyanabba a csaladba tartozzanak, mint a mostani Gondolkodo gomb.

Allapotlogika:

- Gondolkodo ki/be: fuggetlen kapcsolo,
- Obsidian/Excel/stb.: egymas kozt radio-szeru exkluziv valasztas,
- aktiv eszkozmod ujrakattintasa visszavalt "none" allapotra,
- egy eszkozmod valtasa ne torolje a reasoning beallitast.

Peldak:

    reasoning off + no tool       -> sima chat
    reasoning on  + no tool       -> sima chat gondolkodassal
    reasoning off + obsidian      -> Obsidian vault-alapu chat
    reasoning on  + obsidian      -> Obsidian vault-alapu chat gondolkodassal

## Javasolt backend irany

A frontend ne kuldjon nyers LM Studio integrations struktutrat.

Helyette egyszeru alkalmazasszintu payload menjen:

    {
      "content": "...",
      "reasoning_mode": true,
      "tool_mode": "obsidian"
    }

A backend ebbol dontse el:

- milyen provider parameterek kellenek,
- milyen integrations ertek kerul az LM Studio requestbe,
- milyen prompt wrapper kerul a user uzenet melle,
- milyen mod-specifikus hibaellenorzes kell.

Ez megtartja a hatart:

- frontend: termekallapot es UI,
- backend: provider-szerzodes, MCP policy, prompt-kornyezet,
- LM Studio provider: konkret API request osszeallitasa.

## LM Studio szerzodes

Az LM Studio dokumentacio alapjan az MCP eszkozk elerese request-szintu integraciokkal tortenik.

Ket fo irany letezik:

- mcp.json-ban beallitott szerverek hivatkozasa, peldaul `mcp/obsidian`,
- ephemeral MCP szerverek explicit requestbeli megadasa.

A standalone app elso iranya az mcp.json-ban beallitott, elore ismert Obsidian integracio hasznalata legyen.

Fontos elofeltetel:

- LM Studio 0.4.0 vagy ujabb,
- az LM Studio server settingsben engedelyezve legyen az mcp.json szerverek API-bol torteno hivasa,
- ha LM Studio API authentication aktiv, a backend `.env` tartalmazza az `AI_ASSISTANT_LM_STUDIO_API_TOKEN` erteket,
- az Obsidian MCP szerver mukodjon az LM Studio sajat chat feluleten,
- az app configban legyen egyertelmu, hogy az Obsidian mod milyen LM Studio integration id-t hasznal.

## Kontextus es mentes

Az eszkozmod valasztas nem ugyanaz, mint a chat tartalom.

Nyitott dontes, hogy az egyes user uzenetekhez mentsuk-e a hasznalt tool_mode erteket. Iranykent erdemes ugy keszulni, hogy kesobb eltarolhato legyen, mert visszanezesnel hasznos:

    user message: "Dobj ossze..."
    tool_mode: "obsidian"
    reasoning_mode: true

Ugyanakkor az Obsidianbol erkezo tool-call reszletek es intermediate adatok elso korben ne valjanak chat kontextussa.

Alapelv:

> Tool mode metadata is conversation metadata, not extra prompt history.

A kovetkezo modellhivas history-ja tovabbra is a normal user/assistant tartalomra epuljon, kulon dontes nelkul ne injektaljunk vissza tool-call debug adatokat.

## UX visszajelzesek

Az elso korben eleg lehet kompakt allapotjelzes:

- aktiv gomb a composer mod-sorban,
- hiba, ha az Obsidian mod aktiv, de az LM Studio nem tudja hivni az integraciot,
- normal streaming valasz ugyanugy jelenjen meg, mint most.

Kesobb lehet kulon gondolkodni:

- tool-call lepesek minimalis kijelzesen,
- "Obsidian vault hasznalatban" jellegu finom notice-on,
- tool hibak elkulonitett megjelenitesen.

Ezek nem az elso iranyrogzites reszei.

## Elso implementacios irany kesobbre

Ha ebbol kesobb implementacios terv lesz, a legkisebb ertelmes MVP:

1. Backend enum/typing: `tool_mode = none | obsidian`.
2. Config: Obsidian LM Studio integration id, alapertelmezetten `mcp/obsidian`.
3. LM Studio provider: optional integrations atadasa chat requesthez.
4. Chat request schema: tool_mode fogadasa.
5. Obsidian mode prompt wrapper.
6. Frontend composer: Obsidian toggle a Gondolkodo mellett.
7. Exkluziv tool-mode allapotkezeles.
8. Hibakezeles, ha az integration nem elerheto.
9. Manual smoke LM Studio sajat Obsidian MCP konfiguracioval.

Ez meg nem vegleges implementacios terv, csak a varhato elso kis lepes korvonala.

## Dontesi osszefoglalo

- Kevesszamu, explicit tool mode legyen, ne altalanos MCP manager.
- Reasoning es tool mode kulon allapotdimenzio.
- Egyszerre csak egy tool mode lehet aktiv.
- Obsidian az elso tamogatott eszkozmod.
- A user prompt maradjon egyszeru; a backend adja hozza az eszkozmod prompt-kornyezetet.
- Az LM Studio MCP integracio request-szinten keruljon bekotesre.
- Tool-call es intermediate adatok elso korben ne valjanak chat kontextussa.
- A UI-ban a composer alatti mod-sor legyen a termeszetes helye a Gondolkodo es eszkozmod kapcsoloknak.
