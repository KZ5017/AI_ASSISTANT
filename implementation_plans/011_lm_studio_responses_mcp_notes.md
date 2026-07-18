# LM Studio `/v1/responses` + MCP tapasztalati jegyzet

Statusz: kutatasi jegyzet, nem implementacios terv.

## Cel

Rovid osszefoglalo arrol, hogy mit tudtunk meg az LM Studio OpenAI-kompatibilis `/v1/responses` utvonal es MCP eszkozhasznalat kapcsan.

Ez a jegyzet nem irja felul a jelenlegi mukodo iranyt. A jelenlegi app tovabbra is a nativ LM Studio `/api/v1/chat` utvonalat hasznalja.

## Megallapitasok

- A `/v1/chat/completions` utvonal OpenAI-kompatibilis custom tool callingot tud, de az LM Studio `mcp.json`-ban beallitott MCP integraciokat nem kezeli ugy, mint a nativ `/api/v1/chat`.
- A `/v1/chat/completions` tesztben a modell tool-szeru JSON-t irt a valasz szovegebe, de ez nem volt stabil, strukturalt MCP tool execution.
- A `/v1/responses` utvonal remote MCP modban kepes valodi, strukturalt MCP eszkozhivasra.
- A mukodo forma nem az `integrations: ["mcp/excel"]` volt, hanem a `tools` mezoben explicit megadott remote MCP szerver.

Pelda irany:

```json
{
  "tools": [
    {
      "type": "mcp",
      "server_label": "excel",
      "server_url": "http://127.0.0.1:8017/mcp",
      "allowed_tools": ["read_data_from_excel"]
    }
  ]
}
```

## Latott event tipusok

A streaming `/v1/responses` tesztben kulon eventkent jelentek meg:

- `response.mcp_list_tools.*`
- `response.mcp_call.*`
- `response.reasoning_text.delta`
- `response.output_text.delta`
- `response.completed`

Ez technikailag tisztabb szetvalasztast ad, mint a mostani nativ chat stream:

- tool lista,
- tool hivas,
- tool output,
- reasoning,
- vegso assistant valasz.

## Fontos korlat

Az `integrations: ["mcp/excel"]` forma `/v1/responses` alatt nem bizonyult mukodo mcp.json/plugin integracios utnak. A modell ugy viselkedett, mintha nem lenne hozzaferese az Excel MCP-hez.

A `server_url: "mcp/excel"` jellegu probalkozast az endpoint ervenytelen URL-kent elutasitotta.

## Kovetkeztetes

A `/v1/responses` utvonal erdemes lehet kesobbi vizsgalatra, ha:

- strukturaltabb tool eventeket akarunk,
- OpenAI-kompatibilis Responses alapu mukodest akarunk,
- remote MCP szervereket explicit szeretnenk beadni keresenkkent.

Rovid tavon nem indokolt atvaltani, mert a jelenlegi `/api/v1/chat` utvonal mar mukodik az LM Studio `mcp.json` integraciokkal, es az app stream/UI logikaja erre epul.

## Kesobbi nyitott kerdesek

- Erdemes-e a `/v1/responses` utvonalra kulon provider prototipust kesziteni?
- Meg tudjuk-e tartani ugyanazt a UI stream elmenyt a Responses eventekbol?
- Kell-e explicit remote MCP konfiguracio az app backendbe, vagy maradjon az LM Studio `mcp.json` a kozponti hely?
- Stabilabb-e a tool workflow es kevesebb-e a lathato munkanaplozas ezen az utvonalon osszetettebb Excel kerdeseknel?
