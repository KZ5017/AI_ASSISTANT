# LLM provider abstraction es LM Studio Responses provider terv

Statusz: implementalva; F1-F5 kesz, 015-ben a Responses tool activity artifact MVP is kesz.

## Cel

A jelenlegi, stabil LM Studio native kommunikaciot meg kell tartani valtozatlan mukodesi alapkent, es melle kell epitni egy olyan provider absztrakciot, amely configbol valaszthato LLM backendeket tesz lehetove.

Elso uj provider-jelolt: LM Studio OpenAI-compatible `/v1/responses` remote MCP tamogatassal.

A cel nem azonnali provider-valtas, hanem egy tiszta valtokapcsolos architektura:

- a provider configbol valthato; a sablon tovabbra is konzervativ `lm_studio_native`, a helyi aktualis futas `lm_studio_responses`,
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

1. A provider configbol valaszthato; a sablon defaultja `lm_studio_native`, a helyi aktualis futas `lm_studio_responses`.
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

- `lm_studio_native` - konzervativ sablon/default es visszavaltasi ut,
- `lm_studio_responses` - kiprobalt aktualis helyi provider remote MCP tool activity artifactokkal.

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

Status: kesz.

Cel: a mostani native provider marad, csak a valasztasi pont keszul el.

Feladatok:

- `llm_provider.py` alatt `LLMProvider` Protocol/interface definicio,
- `Settings.llm_provider` uj config default `lm_studio_native`,
- `AI_ASSISTANT_LLM_PROVIDER=lm_studio_native` `.env.example` default,
- `get_llm_provider(settings)` factory bevezetese,
- router/service peldanyositasok atvezetese factory-ra,
- tesztek frissitese,
- teszt izolacio: `backend/tests/conftest.py` reseteli a runtime selected chat model allapotot.

Elfogadas:

- default configgal minden ugyanugy mukodik,
- payloadok es SSE eventek nem valtoznak,
- backend tesztek zold: `pytest -q` 42 passed, `ruff check app tests` passed.

### F2 - Responses provider skeleton

Status: kesz.

Cel: minimalis uj provider osztaly, de meg nem production default.

Feladatok:

- `LMStudioResponsesProvider` letrehozasa,
- OpenAI-compatible `/v1/models` vagy native model list dontes teszttel,
- `/v1/responses` non-stream smoke minimalis chathez,
- auth header ujrahasznositasa,
- unsupported load/unload kezeles.

Elfogadas:

- `AI_ASSISTANT_LLM_PROVIDER=lm_studio_responses` mellett a factory a Responses providert valasztja,
- `/v1/models` modelllista es smoke_check tesztelve, loaded-state native fugges miatt `None`,
- `/v1/responses` non-stream chat payload es output parsing tesztelve tool nelkul,
- load/unload es `integrations` hasznalat tudatosan explicit `LLMProviderError`,
- native provider tovabbra is default es valtozatlan.

F2 zaras: `cd backend && .venv/bin/python -m pytest -q` 48 passed, `cd backend && .venv/bin/python -m ruff check app tests` passed.

### F3 - Responses streaming parser

Status: kesz.

Cel: Responses SSE eventek normalizalasa az app jelenlegi `LLMStreamEvent` szerzodesere.

Feladatok:

- `response.output_text.delta` parser,
- `response.reasoning_text.delta` parser,
- `response.completed` final content osszerakas,
- hiba/incomplete mapping,
- parser unit tesztek rogzitett event mintakkal.

Elfogadas:

- frontend valtoztatas nelkul kepes streamelt valaszt kapni,
- `response.output_text.delta` -> `message_delta`,
- `response.reasoning_text.delta` -> `reasoning_delta`,
- `response.completed` -> `done` final contenttel,
- `response.failed` es `response.incomplete` -> `error`,
- tool/MCP lifecycle eventek egyelore `status`,
- reasoning panel ugyanugy mukodik,
- stop tovabbra is connection-abort jellegu.

F3 zaras: `cd backend && .venv/bin/python -m pytest -q` 51 passed, `cd backend && .venv/bin/python -m ruff check app tests` passed.

### F4 - Responses remote MCP adapter

Status: kesz.

Cel: Excel es kesobb Obsidian tool mode remote MCP payloadja.

Feladatok:

- settings remote MCP URL-ek,
- `tool_mode="excel"` -> `tools: [{ type: "mcp", server_label: "excel", server_url: ... }]`,
- allowed_tools opcionális config vagy kod oldali allowlist,
- Obsidian csak akkor keruljon be, ha van stabil remote MCP URL es smoke.

Elfogadas:

- Responses provider `mcp/excel` integraciobol explicit remote MCP `tools` payloadot epit,
- Excel remote MCP URL configbol jon: `AI_ASSISTANT_LM_STUDIO_RESPONSES_EXCEL_MCP_URL`,
- Excel tool payload read-only/informacio-kinyeresi allowlistet kap,
- Obsidian remote MCP URL helye elokeszitve: `AI_ASSISTANT_LM_STUDIO_RESPONSES_OBSIDIAN_MCP_URL`, de uresen explicit hibat ad,
- unknown integration explicit provider hiba,
- non-stream es stream Responses payload is ugyanazt az adaptert hasznalja.

F4 zaras: `cd backend && .venv/bin/python -m pytest -q` 53 passed, `cd backend && .venv/bin/python -m ruff check app tests` passed.

### F5 - Manual provider switch smoke

Status: kesz.

Cel: kontrollalt kezi proba.

Lepesek:

1. default `lm_studio_native` smoke: normal chat, reasoning, Tudásbázis, Adatbázis.
2. `lm_studio_responses` smoke: normal chat, reasoning, Excel remote MCP.
3. visszavaltas `lm_studio_native`-ra egy env ertek atirasaval.

Elfogadas:

- a native ut barmikor visszakapcsolhato,
- nincs adatbazis vagy frontend migracio igeny,
- provider valtas nem valtoztatja meg a mentett chat formatumot.

F5 live smoke eredmeny:

- `.env` provider kapcsolo nem lett atirva; default tovabbra is `lm_studio_native`,
- `lm_studio_native` smoke: reachable, 5 modell, konfiguralt modell elerheto,
- `lm_studio_native` rovid chat smoke auto-load nelkul `qwen/qwen3.5-9b` modellel: `OK`,
- `lm_studio_responses` smoke: reachable, 5 modell, konfiguralt modell elerheto, loaded-state provider oldalon nem ertelmezett,
- `lm_studio_responses` non-stream chat smoke `qwen/qwen3.5-9b` modellel: `OK`,
- `lm_studio_responses` streaming smoke: status/reasoning/message/done eventek jottek, final `OK`,
- `lm_studio_responses` Excel remote MCP streaming smoke: hiba nelkul lefutott, final valasz szerint a `00-INDEX.xlsx` FILES lapjan 1 adatfajl szerepel.

Megjegyzes: a live smoke tudatosan `qwen/qwen3.5-9b` modellel futott, hogy ne kenyszeritsen nagy modell auto-loadot. A production default provider tovabbra is native.

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
- Tool call eventek lathatosaga 015-ben MVP-kent megvalosult kulon `Eszközhasználat` artifacttal; teljes timeline/audit tovabbra is parkolopalyan.
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

1. a jelenlegi native provider ele mar bekerult a tiszta interface es factory,
2. a `/v1/responses` provider skeleton mar masodik valaszthato utkent letezik,
3. a Responses streaming parser kesz,
4. a remote MCP adapter kesz,
5. a kezi provider switch smoke kesz,
6. a Responses tool activity artifact MVP kulon 015 tervben megvalosult,
7. a frontend es assistant service szerzodesek kozben provider-fuggetlenek maradnak,
4. barmikor vissza lehet allni a mostani stabil mukodesre egy config ertekkel.
