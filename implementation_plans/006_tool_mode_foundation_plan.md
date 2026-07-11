# 006 - Tool Mode Foundation Plan

## Cel

Ez a dokumentum a kozos tool mode alapreteget tervezi meg.

Nem egy konkret eszkoz, peldaul Obsidian, implementacios terve. A cel az, hogy az alkalmazas kapjon egy tiszta, tipusos, bovitheto kozos szerkezetet, amelyre kesobb a konkret eszkozmodok sajat tervdokumentumai es implementacioi raepulhetnek.

Ez a terv a `005_mcp_tool_modes_direction.md` iranykijelolo alapveteseire epul, es azokat kovetendo invariansnak tekinti.

## Alapelvek

- A tool mode termekszintu fogalom, nem nyers LM Studio integration objektum.
- A frontend egyszeru alkalmazasallapotot kuld, nem provider-specifikus MCP konfiguraciot.
- A backend donti el, hogy egy tool mode milyen prompt-kornyezetet, integraciot es validaciot igenyel.
- A reasoning mode es a tool mode fuggetlen allapotdimenzio.
- Egyszerre csak egy tool mode lehet aktiv.
- A tool-call intermediate adatok nem kerulnek automatikusan a chat kontextusba.
- A konkret eszkozmodok kesobb sajat tervdokumentumot kapnak.

## Javasolt allapotmodell

Frontend es backend szinten is legyen egy kozos mentalis modell:

    reasoning_mode: boolean
    tool_mode: "none" | "obsidian" | "excel" | ...

Az MVP-ben eleg:

    tool_mode: "none" | "obsidian"

De a szerkezet mar keszuljon ugy, hogy kesobb tovabbi explicit modok felvehetok legyenek.

### Allapotkombinaciok

Pelda ervenyes kombinaciok:

    reasoning off + no tool  -> sima chat
    reasoning on  + no tool  -> sima chat gondolkodassal
    reasoning off + obsidian -> Obsidian mod
    reasoning on  + obsidian -> Obsidian mod gondolkodassal

Ervenytelen vagy nem tamogatott:

    obsidian + excel egyszerre
    frontend altal kuldott nyers integrations payload
    ismeretlen tool_mode csendes elfogadasa

## API szerzodes

A chat send, retry es regenerate szerzodeseket ki kell boviteni tool mode fogadasara.

Javasolt payload:

    {
      "content": "...",
      "reasoning_mode": true,
      "tool_mode": "obsidian"
    }

A `tool_mode` default erteke `none` legyen, hogy a meglevo normal chat viselkedes ne seruljon.

### Send

Uj user uzenet kuldesekor a frontend atadja:

- user content,
- reasoning_mode,
- tool_mode.

A backend:

- validalja a tool_mode erteket,
- kivalasztja a megfelelo tool policy-t,
- a mentett user contentet valtozatlanul, csak a user altal irt szoveggel tarolja,
- a provider requesthez hozzaadja a tool mode prompt-kornyezetet es integraciot.

### Retry / unresolved user resend

Az unresolved user recovery ujrakuldes eseten ugyanazt a tool mode szerzodest hasznalja, mint a normal send.

Nyitott dontes:

- az ujrakuldes a jelenlegi UI tool mode allapotot hasznalja,
- vagy az eredeti user uzenethez mentett tool mode metadata-t.

Foundation szinten erdemes ugy felkeszulni, hogy kesobb mindketto tamogathato legyen.

### Regenerate

Regenerate esetben kulon dontes kell:

- a jelenlegi UI tool mode allapotot hasznalja,
- vagy az eredeti assistant valaszhoz tartozo user uzenet tool mode-jat.

Javasolt MVP:

- a regenerate hasznalja a jelenlegi UI allapotot, ahogy a reasoning toggle eseteben is termeszetszeru,
- kesobb, ha tool_mode metadata mentve van, lehet "eredeti mod szerint ujrageneralas" iranyba finomitani.

## Backend tool mode registry

Kell egy explicit, tipusos registry, amely leirja az ismert tool mode-okat.

Nem cel dinamikus plugin rendszer.

Javasolt modell:

    ToolModePolicy:
      id: "obsidian"
      label: "Obsidian"
      integration_ids: ["mcp/obsidian"]
      prompt_policy: obsidian_prompt_policy
      enabled: bool

Az MVP-ben ez lehet egyszeru Python mapping vagy enum + helper fuggvenyek.

Peldak:

    none:
      integrations: []
      prompt wrapper: nincs

    obsidian:
      integrations: ["mcp/obsidian"]
      prompt wrapper: kesobbi Obsidian terv szerint

## Konfiguracio

A konkret integration id ne legyen szetszorva a kodban.

Javasolt config:

    LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian

Kesobb:

    LM_STUDIO_EXCEL_INTEGRATION_ID=mcp/excel

Az MVP-ben elfogadhato default:

    mcp/obsidian

De a config lehetoseg fontos, mert az LM Studio mcp.json server labelje es integracio id-ja kornyezetenkent elterhet.

### LM Studio API authentication

Az LM Studio MCP/mcp.json API-hozzaferes engedelyezese mellett az LM Studio authentication globalis kovetelmeny lehet. Ha ez aktiv, minden native API hivasnak ugyanazt az `Authorization: Bearer ...` fejlecet kell kuldenie, nem csak a tool mode-os chat hivasoknak.

Foundation kovetelmenyek:

- legyen opcionális backend config: `AI_ASSISTANT_LM_STUDIO_API_TOKEN`,
- ures ertek eseten a provider ne kuldjon Authorization fejlecet,
- beallitott ertek eseten a provider minden LM Studio klienshivasnal kuldje a Bearer tokent,
- a token csak lokalis `.env` titok legyen; `.env.example` csak ures kulcsot tartalmazzon,
- a tool mode registry ne kezeljen authot, mert az provider-szintu keresztmetszeti szerzodes.

## Prompt composition reteg

A tool mode prompt-kornyezet ne a mentett user content resze legyen.

Helyes modell:

    stored user message:
      content = amit a user beirt

    provider request:
      base system/developer context
      + optional tool mode instruction block
      + normal chat history
      + current user content

Ez kulonosen fontos Obsidian modnal, ahol a backend hosszu instrukciot adhat a modellnek a vault-only valaszadasrol.

### Invarians

> Tool prompt wrappers are request context, not stored user text.

Kovetkezmenyek:

- a user altal latott es mentett uzenet tiszta marad,
- a chat tortenet nem telik meg rejtett tool instrukciokkal,
- a tool mode prompt kesobb modosithato anelkul, hogy regi user uzeneteket at kellene irni,
- a context guard tudatosan a vegleges chat tartalomra epulhet.

## Provider integration reteg

Az LM Studio provider kapjon opcionalis integrations parametert.

Javasolt belso szerzodes:

    chat(messages, model, reasoning_mode, integrations=None, ...)

Vagy ha mar van provider options objektum:

    ProviderChatOptions:
      reasoning_mode: bool
      integrations: list[str] | None

Fontos:

- `none` modban ne menjen integrations mezo,
- Obsidian modban a registry/config szerinti integration id menjen,
- a frontend soha ne adhasson at tetszoleges integrations listat.

## LM Studio request forma

A pontos request forma az LM Studio dokumentacio es az app jelenlegi provider-kodja alapjan legyen bekotve.

Foundation szinten a lenyeg:

- legyen helye a request-szintu integrations atadasnak,
- a provider tudja stream es non-stream esetben is ugyanazt a tool opciot,
- tool mode ne torje el a mar meglevo reasoning_delta, delta, done es error esemenyfeldolgozast.

## Metadata es mentes

Foundation szinten erdemes eldonteni, hogy a tool mode metadata kesobb mentheto legyen.

Javasolt irany:

- user message vagy assistant turn kapjon opcionalis `tool_mode` metadata-t,
- reasoning_mode metadata is hasznos lehet visszanezeshez,
- tool-call reszletek elso korben ne legyenek mentve.

MVP-ben a metadata mentes elhalaszthato, de a kodot ne ugy epitsuk, hogy kesobb fajdalmas legyen hozzaadni.

### Kontextus szabaly

> Tool mode metadata is conversation metadata, not extra prompt history.

Ez azt jelenti:

- a tool_mode ertek hasznos lehet UI visszajelzesre,
- de onmagaban nem prompt tartalom,
- nem noveli a 120000 karakteres context guard szovegmennyiseget,
- nem injektal vissza tool-call debug adatokat.

## Frontend composer foundation

A composerben legyen egy kozos mod-sor.

Javasolt szerkezet:

- felso sor: textarea + send/stop button,
- also kompakt sor: mode toggles.

Az also sorban:

- Gondolkodo gomb,
- Obsidian gomb,
- kesobb tovabbi tool mode gombok.

Allapot:

- reasoning gomb: on/off toggle,
- tool gombok: radio-szeru exkluziv allapot,
- aktiv tool gombra ujra kattintva vissza `none` modba,
- disabled allapot kesobb, ha egy tool nincs configolva vagy nem elerheto.

### Komponens-hatar

A composer ne nojon kontrollalatlanul.

Javasolt kulon komponens:

    ComposerModeBar

Felelossege:

- reasoning toggle megjelenitese,
- tool mode gombok megjelenitese,
- active/disabled/hover/pressed allapotok,
- tool mode valtas callback.

Nem felelos:

- provider request osszerakasa,
- LM Studio integrations ismerete,
- tool prompt logika.

## Hibakezeles

Kozos hibak, amelyeket mar foundation szinten erdemes kezelni:

- ismeretlen tool_mode,
- tool mode nincs engedelyezve backend configban,
- integration id hianyzik,
- LM Studio API elutasitja az integrations mezot,
- LM Studio szerint az MCP server nem hivhato,
- tool-call kozbeni provider error.

UI szinten ezek a mar meglevo notice/error rendszerhez kapcsolodjanak.

Fontos, hogy egy Obsidian hiba ne altalanos "chat failed" uzenetkent jelenjen meg, ha tudunk pontosabbat mondani.

Peldak:

    Az Obsidian eszkozmod nincs beallitva.
    Az LM Studio nem engedelyezi az mcp.json szerverek API-bol torteno hivasat.
    Az Obsidian MCP szerver nem erheto el.

## Tesztelesi terv

### Backend unit tesztek

- `none` tool mode nem ad integrations-t.
- `obsidian` tool mode a config szerinti integration id-t adja.
- ismeretlen tool mode validacios hibat ad.
- tool prompt wrapper nem irja at a mentett user contentet.
- reasoning_mode es tool_mode egyutt atmegy a provider options retegen.

### Backend service tesztek

- send normal modban ugyanugy mukodik, mint eddig.
- send Obsidian modban tool policy-t hasznal.
- streaming valasz es reasoning_delta feldolgozas nem serul tool mode mellett.
- abort/stop nem hagy felig mentett tool artifactot.

### Frontend tesztek/manual smoke

- mode sor megjelenik.
- Gondolkodo es tool mode kulon kapcsolhato.
- egyszerre csak egy tool lehet aktiv.
- aktiv tool ujrakattintva kikapcsol.
- send payload tartalmazza a tool_mode erteket.
- normal chat flow `none` modban valtozatlan.

## Implementacios lepesek

1. Backend tool mode enum es validacio bevezetese.
2. Chat request schema-k bovitese `tool_mode` mezovel, default `none` ertekkel.
3. Tool mode registry/policy reteg letrehozasa.
4. Config mezok felvetele az elso integration id-hoz, Obsidian defaulttal.
5. Prompt composition helper bevezetese, egyelore `none` es placeholder Obsidian policy-val.
6. LM Studio provider options bovitese optional integrations mezovel.
7. Streaming es regenerate/retry kodutak atvezetese az uj provider options szerzodesre.
8. Backend tesztek a registry, payload es provider options viselkedesre.
9. Frontend tool mode tipus es allapot bevezetese.
10. ComposerModeBar komponens letrehozasa.
11. Chat send/regenerate/retry payloadok tool_mode mezovel bovitese.
12. Frontend build es manual smoke normal `none` modban.
13. Obsidian-specifikus tervdokumentum megirasa erre a foundationre hivatkozva.

## Elvalasztas a kovetkezo Obsidian tervtol

Ez a foundation terv nem donti el reszletesen:

- pontos Obsidian prompt szoveg,
- `00-INDEX.md` hasznalati instrukcio vegleges formaja,
- Obsidian MCP server konkret neve vagy telepitese,
- Obsidian tool-call UI megjelenitese,
- vault-only valaszadas teszt promptjai.

Ezek egy kulon Obsidian tool mode tervdokumentumba tartoznak.

## Nyitott dontesek

- Mentsuk-e mar az MVP-ben a tool_mode metadata-t uzenetszinten?
- Regenerate a jelenlegi UI tool mode-ot vagy az eredeti uzenet tool mode-jat hasznalja?
- Kell-e backend endpoint a tamogatott tool mode-ok listazasara, vagy eleg frontend oldali statikus lista az elso korben?
- Legyen-e UI disabled allapot, ha a backend szerint egy tool nincs configolva?
- Mutassunk-e minimalis tool-call aktivitast stream kozben, vagy az elso korben maradjon csak a normal streaming valasz?

## Dontesi osszefoglalo

- Eloszor tool mode foundationt epitsunk, ne Obsidianra kemenyitett megoldast.
- A frontend termekszintu `tool_mode` allapotot kuldjon.
- A backend registry/policy reteg forditsa ezt prompt-kornyezette es LM Studio integrations beallitassa.
- A user content maradjon tiszta, a tool prompt wrapper csak provider request context legyen.
- A composer kapjon kozos mode sort, amelyben a reasoning es az eszkozmodok egy helyen kezelhetok.
- A konkret Obsidian implementacio kulon tervdokumentumban kovesse ezt a foundationt.
