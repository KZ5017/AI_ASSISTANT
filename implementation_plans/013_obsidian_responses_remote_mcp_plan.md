# 013 - Obsidian Responses Remote MCP Plan

Statusz: implementacios terv; F1-F3 kesz.

## Cel

A `lm_studio_responses` provider alatt is hasznalhato legyen a Tudásbázis/Obsidian tool mode, ugyanazzal a termekviselkedessel, amit a native provider alatt mar elfogadtunk.

Ez nem valtja le a jelenlegi stabil native utat. A default tovabbra is:

```bash
AI_ASSISTANT_LLM_PROVIDER=lm_studio_native
```

A cel az, hogy kesobb a provider-valtas configbol tortenhessen, es a Tudásbázis mod ne legyen native-providerhez kotve.

## Mire epul

Ez a terv a kovetkezo dokumentumokra epul:

- `005_mcp_tool_modes_direction.md` - MCP/tool mode magas szintu alapvetes,
- `006_tool_mode_foundation_plan.md` - kozos tool mode foundation,
- `007_obsidian_tool_mode_plan.md` - native provider alatti Obsidian/Tudásbázis viselkedes,
- `011_lm_studio_responses_mcp_notes.md` - LM Studio `/v1/responses` + remote MCP kutatasi jegyzet,
- `012_llm_provider_abstraction_and_responses_provider.md` - provider abstraction, Responses skeleton, streaming, Excel remote MCP adapter es provider switch smoke.

## Kiindulo allapot

### Native provider

`lm_studio_native` alatt a Tudásbázis mod mukodik:

- a frontend `tool_mode: "obsidian"` erteket kuld,
- a backend a `ToolModePolicy` alapjan `integration_ids=("mcp/obsidian",)` erteket ad,
- a native provider ezt `integrations: ["mcp/obsidian"]` payloadkent kuldi az LM Studio native `/api/v1/chat` endpointnak,
- a Tudásbázis system prompt bekerul a provider request contextbe,
- a user prompt tisztan mentodik.

### Responses provider

`lm_studio_responses` alatt mar kesz:

- provider factory,
- `/v1/models` smoke/list,
- `/v1/responses` non-stream chat,
- `/v1/responses` streaming parser,
- Excel remote MCP adapter,
- Excel remote MCP live smoke.

Obsidiannal kapcsolatban jelenleg csak az elokeszites van meg:

- config hely: `AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_URL`,
- provider-side payload builder,
- ures URL eseten explicit provider error.

Meg nincs kesz:

- pontos Obsidian remote MCP URL szerzodes,
- opcionális remote MCP header/auth szerzodes, ha az Obsidian MCP server igenyli,
- Obsidian remote MCP allowed-tools dontes,
- live smoke Responses providerrel,
- dokumentalt provider-valtas lepes Tudásbázis moddal.

## Fontos kulonbseg a native es Responses ut kozott

Native provider:

```json
{
  "integrations": ["mcp/obsidian"]
}
```

Responses provider:

```json
{
  "tools": [
    {
      "type": "mcp",
      "server_label": "obsidian",
      "server_url": "..."
    }
  ]
}
```

Responses alatt nem az LM Studio `mcp.json` integration id-t adjuk at kozvetlenul, hanem explicit remote MCP szerver URL-t.

## Tervezett config

Minimalis config:

```bash
AI_ASSISTANT_LLM_PROVIDER=lm_studio_responses
AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_URL=https://127.0.0.1:27124/mcp/
```

Ha az Obsidian MCP szerver Bearer tokent igenyel, akkor kulon header/token config kell. Ezt nem szabad osszekeverni az LM Studio API tokennel.

Javasolt kesobbi config:

```bash
AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_TOKEN=
```

Provider payloadban:

```json
{
  "type": "mcp",
  "server_label": "obsidian",
  "server_url": "https://127.0.0.1:27124/mcp/",
  "headers": {
    "Authorization": "Bearer ..."
  }
}
```

Ha a live smoke alapjan az LM Studio `/v1/responses` remote MCP schema nem fogad `headers` mezot, akkor ezt a reszt kulon kell kezelni vagy el kell vetni.

## Obsidian allowed-tools dontes

Az Excel remote MCP adapter read-only allowlistet kapott, mert az Excel MCP szerver sok iro/modosito toolt is tartalmaz.

Obsidiannal ugyanez az elv helyes:

- Tudásbázis modban csak olvasasi/informacio-kinyeresi eszkozok legyenek engedelyezve,
- tilos jegyzetet letrehozni, modositani, torolni, atnevezni vagy athelyezni,
- a system prompt tiltasa mellett provider payload szinten is probaljuk szukiteni az eszkozkeszletet, ha az LM Studio remote MCP ezt tamogatja.

Konkreten elobb fel kell terkepezni az Obsidian MCP tool neveit. Csak ez utan legyen vegleges allowlist.

MVP-ben ket lepcso elfogadhato:

1. elso live smoke allowlist nelkul, hogy kideruljon, a remote Obsidian MCP egyaltalan hivhato-e,
2. masodik kor read-only allowlisttel, ha ismert a pontos tool lista.

## Implementacios lepesek

### F1 - Obsidian remote MCP URL es opcionális token config

Status: kesz.

Feladatok:

- `Settings` bovites opcionális Obsidian remote MCP tokennel, ha kell,
- `.env.example` bovites,
- ures URL tovabbra is explicit provider error legyen,
- token ures string -> `None`.

Elfogadas:

- config nelkul a Responses Obsidian tool mode nem csendben hibazik, hanem ertheto provider errorral,
- token nelkul tovabbra is lehet smoke-olni, ha a server nem igenyel headert,
- `Settings.lm_studio_responses_obsidian_mcp_token` bekerult,
- `.env.example` tartalmazza az `AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_TOKEN` sort,
- ures URL es ures token `None` ertekkel kezelodik.

F1 zaras: `cd backend && .venv/bin/python -m pytest tests/test_lm_provider.py -q` 25 passed.

### F2 - Responses Obsidian MCP payload veglegesitese

Status: kesz.

Feladatok:

- `_responses_obsidian_mcp_tool(settings)` payload kiegeszitese a live schema szerint,
- ha a remote MCP `headers` tamogatott es token van, bekerul az Authorization header,
- ha ismert read-only tool lista van, `allowed_tools` bekerul,
- unknown/unsupported integration tovabbra is explicit hiba.

Elfogadas:

- unit teszt payloadra token nelkul,
- unit teszt payloadra tokennel, ha header tamogatott,
- unit teszt ures URL hibara.

F2 zaras:

- az Obsidian Responses MCP builder token nelkul type/server_label/server_url payloadot ad,
- tokennel headers.Authorization Bearer mezot is ad,
- ures Obsidian remote MCP URL tovabbra is explicit provider error,
- Obsidian allowed_tools szandekosan nincs meg rogzitve: live tool-listazas utan szabad csak read-only allowlistet veglegesiteni, mert a pontos tool nevek szerverfuggok,
- unit lefedes bekerult a token nelkuli es tokenes payload szerzodesre,
- celzott ellenorzes: cd backend && .venv/bin/python -m pytest tests/test_lm_provider.py -q -> 27 passed.

### F3 - Live smoke Responses providerrel

### F3 status - live smoke

Status: kesz.

Elso probakor:

- a Responses provider elindult es status/MCP lifecycle eventeket adott,
- az LM Studio Responses API mcp_list_tools lepese az obsidian remote MCP szervernel elakadt,
- hiba: Unable to connect to remote MCP server obsidian at url https://127.0.0.1:27124/mcp/,
- Windows oldali TCP port ellenorzes: 127.0.0.1:27124 nyitva,
- token nelkuli HTTPS GET cert ellenorzes kihagyasaval 401 Unauthorized valaszt adott,
- kovetkeztetes: az Obsidian MCP endpoint el, de auth kell; a tokenes F3 smoke ezutan sikeresen lefutott.
- tokenes F3 smoke qwen/qwen3.5-9b modellel error nelkul lefutott,
- Smoke 1 eredmeny: a vault fo temakorait a 00-INDEX.md + jegyzet flow alapjan osszefoglalta,
- Smoke 3 hianyteszt eredmeny: nem hallucinalt, kimondta, hogy nincs Mars-koloniak mezogazdasagi adozasarol szolo vault dokumentacio.

Elokeszites:

- Obsidian MCP server fusson,
- a vaultban legyen `00-INDEX.md`,
- az Obsidian MCP server remote URL-je legyen beallitva,
- LM Studio API authentication token maradjon LM Studio provider szintu config, ha az LM Studio megkoveteli.

Smoke 1 - tool elerhetoseg:

```text
Olvasd el a 00-INDEX.md fájlt, és válaszolj egy rövid mondatban, hogy milyen fő témákat tartalmaz a vault.
```

Smoke 2 - vault-only viselkedes:

```text
Mutasd be röviden, hogyan érdemes használni ezt az alkalmazást.
```

Elvart eredmeny:

- a valasz a vault app-dokumentacios jegyzeteibol jon,
- nem altalanos Obsidian/MCP magyarazat,
- ha nincs relevans jegyzet, ezt mondja ki.

Smoke 3 - hianyteszt:

```text
Válaszolj egy olyan témáról, amely biztosan nincs a vaultban.
```

Elvart eredmeny:

- nem hallucinal,
- pontosítast ker vagy kimondja, hogy nincs eleg vault-adat.

## Provider-valtas felhasznaloi lepes

Ha minden smoke rendben van, a provider valtas a felhasznalo oldalan csak `.env` modositas legyen:

Native:

```bash
AI_ASSISTANT_LLM_PROVIDER=lm_studio_native
```

Responses:

```bash
AI_ASSISTANT_LLM_PROVIDER=lm_studio_responses
AI_ASSISTANT_LM_STUDIO_RESPONSES_EXCEL_MCP_URL=http://127.0.0.1:8017/mcp
AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_URL=https://127.0.0.1:27124/mcp/
```

Majd app restart.

Fontos: a valtashoz ne kelljen frontend kodot, backend kodot vagy adatbazis formatumot modositani.

## Nem cel ebben a korben

- production default atvaltasa `lm_studio_responses` providerre,
- Obsidian tool-call timeline UI,
- Obsidian tool output mentese kulon artifactkent,
- sajat Obsidian indexeles vagy RAG,
- tobb tool mode egyideju hasznalata,
- Obsidian MCP szerver telepitese vagy menedzselese az appbol.

## Kockazatok

- Az Obsidian MCP server remote URL-je es auth/header szerzodese elterhet az Excel MCP HTTP szerveretol.
- Az LM Studio `/v1/responses` remote MCP schema lehet, hogy nem tamogatja ugyanugy a `headers` mezot.
- Az Obsidian MCP tool nevei szerverfuggoek lehetnek, ezert az allowlistet csak live tool-listazas utan szabad veglegesiteni.
- Ha nincs read-only allowlist, a prompt policy tiltasa fontos, de onmagaban nem olyan eros, mint a payload-szintu szukites.

## Lezarasi feltetel

Ez a terv akkor tekintheto kesznek, ha:

- a Responses provider Obsidian remote MCP URL-lel kepes Tudásbázis modban valaszolni,
- a valasz a `00-INDEX.md` + relevans jegyzet flow-t koveti,
- native provider tovabbra is mukodik,
- a provider-valtas dokumentalt `.env` szintu muvelet,
- tesztek es live smoke eredmenyek frissitve vannak az allapotfajlokban.
