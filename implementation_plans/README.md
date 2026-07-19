# Implementation Plans

Ez a mappa olyan reszletes dokumentumterveket tartalmaz, amelyek alapjan kesobb mar kodolni lehessen, ne ujratervezni.

## Tervek

1. `001_lm_studio_streaming_responses.md` - LM Studio streaming assistant valaszok backend/frontend implementacios terve.
2. `002_error_notice_ux.md` - Egyseges hiba-, warning- es notice-megjelenites finomitasi terve, modellpanel notice-okkal egyutt.
3. `003_reasoning_delta_ui.md` - Futas kozbeni, atmeneti `reasoning_delta` / Gondolatmenet UI implementacios terve.
4. `004_saved_reasoning_artifacts.md` - Mentett, de kontextusbol kizart reasoning / Gondolatmenet artifactok implementacios terve.
5. `005_mcp_tool_modes_direction.md` - MCP/tool mode iranykijelolo alapvetes Obsidian es kesobbi konkret eszkozmodokhoz.
6. `006_tool_mode_foundation_plan.md` - Kozos tool mode foundation implementacios terv a kesobbi konkret eszkozmodok ala.
7. `007_obsidian_tool_mode_plan.md` - Obsidian MCP tool mode implementacios terv a 005/006 alapokra epitve; tartalmazza az LM Studio API authentication/token elofeltetelt, manual smoke statuszt es a szigoritott magyar Tudásbázis prompt policy aktualis allapotat.
8. `008_markdown_content_layout_hygiene.md` - Assistant Markdown tartalmak szelessegbiztos CSS/layout terve code blockokhoz, tablazatokhoz es hosszu nem torheto szovegekhez.
9. `009_excel_tool_mode_plan.md` - Excel/Adatbazis tool mode implementacios terve a 005/006 alapokra epitve; roviditett index-router, read-only Excel tablazatos kerdes-valasz/informaciokinyeres MVP kesz, file picker es automatikus discovery parkolopalyan.
10. `010_chat_thread_render_performance.md` - Hosszabb chatfolyamok melletti composer/recovery editor reszponzivitas es MessageThread render performance finomitasi terve; elso memoizacios kor kesz.
11. `011_lm_studio_responses_mcp_notes.md` - Kutatasi jegyzet az LM Studio OpenAI-kompatibilis `/v1/responses` endpoint es remote MCP eszkozhivas tapasztalatairol.
12. `012_llm_provider_abstraction_and_responses_provider.md` - Configbol valaszthato LLM provider absztrakcio es LM Studio `/v1/responses` remote MCP provider implementacios terve.
13. `013_obsidian_responses_remote_mcp_plan.md` - Obsidian/Tudásbázis tool mode Responses-provider alatti remote MCP bekotesenek es smoke-janak terve; F1-F2 config/token es payload/header unit lefedes kesz; F3 live smoke tokenes auth-tal sikeresen lefutott.
14. `014_external_model_lifecycle_plan.md` - Implementalva: az appbol torteno modellvalasztas, load/unload es chatkuldes kozbeni auto-load kivezetve; LM Studio kezeli a modell eletciklust, az app csak allapotot jelez es betoltott konfiguralt modell mellett kuld.
15. `015_responses_tool_activity_artifacts.md` - Implementalva: Responses-provider alatti strukturalt MCP/tool activity levalasztasa, mentett UI-only `Eszközhasználat` artifact es listás Markdown megjelenites.
16. `016_responses_final_answer_separation.md` - Implementalva: Responses-provider alatti final answer es modell-munkanarracio strukturalt, stream utani szetvalasztasa; final content tisztitasa es UI-only Munkalepesek artifact.
17. `017_tool_mode_user_prompt_call_frame.md` - Implementalva: tool modokban csak az aktualis legutolso user prompt modellhivasi keretezese forrasellenorzesi fegyelem javitasara, DB/context szennyezes nelkul.
