# LLM provider abstraction es LM Studio Responses provider terv

Statusz: implementacios terv.

## Cel

A jelenlegi, stabil LM Studio native kommunikaciot meg kell tartani valtozatlan mukodesi alapkent, es melle kell epitni egy olyan provider absztrakciot, amely configbol valaszthato LLM backendeket tesz lehetove.

Elso uj provider-jelolt: LM Studio OpenAI-compatible `/v1/responses` remote MCP tamogatassal.

A cel nem azonnali provider-valtas, hanem egy tiszta valtokapcsolos architektura:

- a mostani `lm_studio_native` marad default,
- a backend service reteg ne tudja, milyen API ut van alatta,
- kesobb uj provider bevezetese ne igenyeljen assistant service / router / frontend atirast.

## Kiindulo allapot

Jelenleg a mukodo provider:

- `backend/app/llm_provider.py` fajlban van,
- neve: `LMStudioNativeProvider`,
- natív LM Studio endpointokat hasznal:
  - `/api/v1/models`,
  - `/api/v1/models/load`,
  - `/api/v1/models/unload`,
  - `/api/v1/chat`,
- tool mode-oknal LM Studio `integrations` payloadot kuld:
  - `mcp/obsidian`,
  - `mcp/excel`,
- stream esemenyeket a jelenlegi app-szintu `LLMStreamEvent` tipusra normalizal.

Ez mukodik es stabil. Ezt a mukodest nem szabad lebontani.

## OpenAI-compatible kutatasi eredmeny

Rogzitett jegyzet: `implementation_plans/011_lm_studio_responses_mcp_notes.md`.

Lenyeg:

- `/v1/chat/completions` nem jo irany LM Studio `mcp.json` integraciokhoz,
- `/v1/responses` remote MCP formaban valodi strukturalt MCP eventeket ad,
- a mukodo forma explicit remote MCP tool config:

```json
{
  "tools": [
    {
      "type": "mcp",
      "server_label": "excel",
      "server_url": "http://127.0.0.1:8017/mcp"
    }
  ]
}
```

- az `integrations: ["mcp/excel"]` forma `/v1/responses` alatt nem bizonyult mukodonek.

## Fo dontesek

1. A default provider marad `lm_studio_native`.
2. A provider valasztas configbol tortenik.
3. Az assistant service tovabbra is provider-fuggetlen szerzodest hasznal.
4. A tool mode policy domain oldalon marad, de provider-specifikus payloadra kulon adapter forditja.
5. A frontend SSE szerzodes nem valtozhat a provider-valtas miatt.
6. A `/v1/responses` provider csak akkor kap production hasznalati statuszt, ha ugyanazokat a fobb flow-kat stabilan tudja, mint a native provider.

## Javasolt config

Uj env:

```bash
AI_ASSISTANT_LLM_PROVIDER=lm_studio_native
```

Tamogatott kezdeti ertekek:

- `lm_studio_native` - default, jelenlegi stabil mukodes,
- `lm_studio_responses` - kesobbi uj provider.

Responses providerhez kesobbi env-ek:

```bash
AI_ASSISTANT_LM_STUDIO_RESPONSES_BASE_URL=http://127.0.0.1:1234
AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_URL=
AI_ASSISTANT_LM_STUDIO_RESPONSES_EXCEL_MCP_URL=http://127.0.0.1:8017/mcp
```

Megfontolas:

- lehet ugyanazt a `lm_studio_base_url` erteket hasznalni, ha az LM Studio host azonos,
- remote MCP URL-eket kulon kell kezelni, mert Responses alatt nem eleg az `mcp/excel` integracio id.

## Provider interface

A backend tobbi resze elott egy kozos interface maradjon.

Minimalis szerzodes:

```python
class LLMProvider(Protocol):
    provider_name: str

    def list_models(self) -> list[LLMModel]: ...
    def smoke_check(self, selected_chat_model: str | None = None) -> LLMSmokeResult: ...
    def loaded_model_instance_ids(self) -> list[str]: ...
    def ensure_chat_model_loaded(self, model_id: str) -> str: ...
    def load_chat_model(self, model_id: str) -> LLMModelLoadResult: ...
    def unload_chat_model(self, model_id: str) -> LLMModelUnloadResult: ...
    def chat_completion(...) -> LLMChatCompletion: ...
    def chat_completion_stream(...) -> Iterator[LLMStreamEvent]: ...
```

Fontos: ha egy kesobbi provider nem tud model load/unload funkciot, akkor azt nem szabad csendben hamisitani. Ket lehetoseg:

- `LLMProviderError("Model load is not supported by this provider")`,
- vagy capability mezo bevezetese `LLMProviderCapabilities` tipussal.

Elso korben eleg lehet a hibat visszaadni, mert a native provider marad default.

## Provider factory

Javasolt uj helper:

```python
def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    if settings.llm_provider == "lm_studio_native":
        return LMStudioNativeProvider(settings)
    if settings.llm_provider == "lm_studio_responses":
        return LMStudioResponsesProvider(settings)
    raise LLMProviderError(...)
```

Cel:

- router/service kod ne peldanyositson direkt `LMStudioNativeProvider`-t,
- tesztekben tovabbra is lehessen fake providert beadni,
- a jelenlegi native provider importok fokozatosan valthatok legyenek factory-ra.

## Tool mode adapter

A tool mode domain szerzodes marad `backend/app/tool_modes.py` alatt:

- `none`,
- `obsidian`,
- `excel`,
- prompt policy,
- tool mode label,
- abstract tool intent.

A provider-specifikus payloadot kulon kell forditani.

Native provider:

```python
ToolModePolicy(..., integration_ids=("mcp/excel",))
# payload: { "integrations": ["mcp/excel"] }
```

Responses provider:

```python
ToolModePolicy(..., remote_mcp_tools=(...))
# payload: { "tools": [{ "type": "mcp", "server_url": "http://127.0.0.1:8017/mcp" }] }
```

Elso implementacios korben nem kotelezo a `ToolModePolicy` tipust tul nagyra boviteni. Lehet provider oldalon configbol mapelni:

- `excel` -> `settings.lm_studio_responses_excel_mcp_url`,
- `obsidian` -> `settings.lm_studio_responses_obsidian_mcp_url`.

Hosszu tavon tisztabb egy `ToolModeRuntime` vagy `ToolModeProviderPayload` adapter.

## Stream event normalizalas

A frontend jelenlegi SSE szerzodese marad:

- `start`,
- `delta`,
- `reasoning_delta`,
- `status`,
- `error`,
- `done`.

Native `/api/v1/chat` eventek mar erre vannak forditva.

Responses provider mapping:

- `response.output_text.delta` -> `LLMStreamEvent(type="delta")`,
- `response.reasoning_text.delta` -> `LLMStreamEvent(type="reasoning_delta")`,
- `response.mcp_list_tools.*` -> opcionálisan `status` vagy teljesen internal,
- `response.mcp_call.*` -> opcionálisan `status` vagy internal,
- `response.completed` -> `done` final contenttel,
- `response.failed` / HTTP hiba -> `error`.

Fontos UX dontes:

- MVP-ben a tool call eventeket nem kell lathatova tenni.
- A frontend ne valtozzon provider-specifikussa.
- Ha kesobb tool timeline kell, az kulon feature legyen.

## Implementacios bontas

### F1 - Provider interface es factory, viselkedesvaltozas nelkul

Cel: a mostani native provider marad, csak a valasztasi pont keszul el.

Feladatok:

- `llm_provider.py` vagy uj `llm_provider_base.py` alatt `Protocol`/interface definicio,
- `Settings.llm_provider` uj config default `lm_studio_native`,
- provider factory bevezetese,
- router/service peldanyositasok atvezetese factory-ra,
- tesztek frissitese.

Elfogadas:

- default configgal minden ugyanugy mukodik,
- payloadok es SSE eventek nem valtoznak,
- backend tesztek zold.

### F2 - Responses provider skeleton

Cel: minimalis uj provider osztaly, de meg nem production default.

Feladatok:

- `LMStudioResponsesProvider` letrehozasa,
- OpenAI-compatible `/v1/models` vagy native model list dontes teszttel,
- `/v1/responses` non-stream smoke minimalis chathez,
- auth header ujrahasznositasa,
- unsupported load/unload kezeles.

Elfogadas:

- `AI_ASSISTANT_LLM_PROVIDER=lm_studio_responses` mellett smoke_check ertelmes hibat vagy ready allapotot ad,
- normal chat tool nelkul mukodik vagy egyertelmu hibat ad,
- native provider tovabbra is valtozatlan.

### F3 - Responses streaming parser

Cel: Responses SSE eventek normalizalasa az app jelenlegi `LLMStreamEvent` szerzodesere.

Feladatok:

- `response.output_text.delta` parser,
- `response.reasoning_text.delta` parser,
- `response.completed` final content osszerakas,
- hiba/incomplete mapping,
- parser unit tesztek rogzitett event mintakkal.

Elfogadas:

- frontend valtoztatas nelkul kepes streamelt valaszt kapni,
- reasoning panel ugyanugy mukodik,
- stop tovabbra is connection-abort jellegu.

### F4 - Responses remote MCP adapter

Cel: Excel es kesobb Obsidian tool mode remote MCP payloadja.

Feladatok:

- settings remote MCP URL-ek,
- `tool_mode="excel"` -> `tools: [{ type: "mcp", server_label: "excel", server_url: ... }]`,
- allowed_tools opcionális config vagy kod oldali allowlist,
- Obsidian csak akkor keruljon be, ha van stabil remote MCP URL es smoke.

Elfogadas:

- Excel MCP-n legalabb egy read-only smoke lefut,
- tool call eventek strukturaltan jonnek,
- vegso assistant valasz ugyanabban az app SSE formatumban erkezik.

### F5 - Manual provider switch smoke

Cel: kontrollalt kezi proba.

Lepesek:

1. default `lm_studio_native` smoke: normal chat, reasoning, Tudásbázis, Adatbázis.
2. `lm_studio_responses` smoke: normal chat, reasoning, Excel remote MCP.
3. visszavaltas `lm_studio_native`-ra egy env ertek atirasaval.

Elfogadas:

- a native ut barmikor visszakapcsolhato,
- nincs adatbazis vagy frontend migracio igeny,
- provider valtas nem valtoztatja meg a mentett chat formatumot.

## Tesztelesi terv

Backend unit tesztek:

- provider factory default `lm_studio_native`,
- ismeretlen provider nev hibat dob,
- native provider tovabbra is `integrations` payloadot kuld,
- responses provider `tools` payloadot epit remote MCP-hez,
- responses SSE parser mapping:
  - output delta,
  - reasoning delta,
  - mcp call event internal/status,
  - completed final.

Manual smoke:

- normal chat native providerrel,
- Excel/Adatbázis native providerrel,
- `/v1/responses` provider tool nelkul,
- `/v1/responses` provider Excel remote MCP-vel,
- provider visszavaltas native-ra.

## Kockazatok

- LM Studio `/v1/responses` viselkedese verziofuggo lehet.
- Remote MCP URL-eket kulon kell karbantartani, nem eleg az LM Studio `mcp.json` integration id.
- Model load/unload lehet, hogy responses provider alatt tovabbra is native endpointokra szorul, vagy nem lesz tamogatott.
- Tool call eventek lathatosaga/eltuntetese UX dontes lesz, de MVP-ben marad internal.
- A 9B-s lokalis modell toolhasznalata promptfuggo marad; az API ut tisztabb eventeket adhat, de nem teszi automatikusan okosabba a modellt.

## Nem cel ebben a korben

- A jelenlegi native provider lecserelese.
- Frontend provider-specifikus UI.
- Tool call timeline vagy audit panel.
- OpenAI felhos API bekotese.
- vLLM/Ollama provider implementacio.
- MCP szerverek automatikus discovery-je.

## Osszegzes

A helyes irany egy konzervativ provider-abstraction refaktor:

1. eloszor a jelenlegi native provider ele kerul tiszta interface es factory,
2. utana keszulhet el a `/v1/responses` provider mint masodik valaszthato ut,
3. a frontend es assistant service szerzodesek kozben valtozatlanok maradnak,
4. barmikor vissza lehet allni a mostani stabil mukodesre egy config ertekkel.
