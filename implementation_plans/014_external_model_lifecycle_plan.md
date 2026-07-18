# 014 - External Model Lifecycle Plan

Statusz: implementacios terv; kodolas elott.

## Cel

A modell eletciklus kezelese keruljon ki az alkalmazasbol. Az app ne toltson be, ne valasszon le es ne auto-loadoljon modelleket. A modellmenedzsment az LM Studio feladata legyen.

Az app feladata:

- modellallapot lekerdezese,
- betoltott es hasznalhato modell allapot jelzese,
- chat kuldese csak akkor, ha van hasznalhato betoltott modell,
- ertheto hiba, ha nincs hasznalhato modell.

Ez a terv szandekosan egységesiti a lm_studio_native es lm_studio_responses providerek szerzodeset: egyik ut se vegezzen rejtett modellmenedzsmentet chatkuldes kozben.

## Termekdontes

A korabbi kenyelmi modell kivezetesre kerul:

- UI-ban modell kivalasztasa,
- appbol modell betoltese,
- appbol modell levalasztasa,
- chatkuldes elott automatikus modellbetoltes.

Az uj modell:

- a felhasznalo az LM Studio-ban tolti be vagy valasztja le a modelleket,
- az app csak figyeli az allapotot,
- az app chatre azt a modellt hasznalja, amely a stabil szabalyok szerint hasznalhato,
- ha nincs hasznalhato modell, nincs rejtett javitas vagy auto-load, hanem hiba vagy UI blokkolas van.

## Mi nem cel

- Nem cel LM Studio vezerlopultot epiteni.
- Nem cel provider-valto UI kapcsolo.
- Nem cel Responses provider ala native load/unload hidat epiteni.
- Nem cel model load/unload endpointok azonnali fizikai torlese, ha a visszafele kompatibilitas miatt elobb soft-deprecate tisztabb.
- Nem cel adatbazis-migracio.

## Jelenlegi allapot

### Backend config

backend/app/config.py jelenleg tartalmazza:

- lm_studio_chat_model: konfiguralt default chat modell,
- lm_studio_auto_load_chat_model: jelenleg True,
- native load-profil parameterek: context length, eval batch, flash attention, KV cache offload.

Ezek kozul az auto-load es a load-profil parameterek az appbol torteno modellbetolteshez kotodnek. Az uj celmodellben ezek vagy kivezethetok, vagy legacy/deprecated configkent maradnak, de chatkuldes kozben nem hasznalhatok.

### Runtime selected model

backend/app/model_runtime.py jelenleg globalis process-szintu selected chat model allapotot tart:

- get_selected_chat_model(settings),
- set_selected_chat_model(model_id),
- reset_selected_chat_model().

Ez jelenleg lehetove teszi, hogy a UI modellvalasztoja felulirja a konfiguralt modelt anelkul, hogy az LM Studio oldali tenyleges betoltott modellallapot garantalt lenne.

Az uj celmodellben ez a runtime selected-model allapot nem kivanatos. A modellkivalasztas ne legyen az app sajat allapota. A hasznalt modellnek a konfiguraciobol es az LM Studio tenyleges betoltott allapotabol kell kovetkeznie.

### Native provider

backend/app/llm_provider.py native providerben a rejtett auto-load jelenleg a chat_completion es chat_completion_stream metodusokban tortenik.

A jelenlegi lenyeg:

- ha lm_studio_auto_load_chat_model igaz, a provider meghivja az ensure_chat_model_loaded folyamatot,
- az ensure_chat_model_loaded ha nem talal betoltott instance-t, meghivja a native /api/v1/models/load endpointot,
- ez chatkuldes kozbeni mellekhatas.

Ez az a viselkedes, amit ki kell vezetni.

A native provider tovabba tartalmaz direkt load/unload funkciokat:

- load_chat_model,
- load_configured_chat_model,
- unload_chat_model,
- unload_configured_chat_model,
- unload_model_instance.

Ezek backendben elso korben maradhatnak legacy vagy deprecated kodkent, de a publikus app flow es UI ne hasznalja oket.

### Responses provider

LMStudioResponsesProvider jelenleg nem tolt be vagy valaszt le modellt. Ez osszhangban van az uj celmodellel.

Jelenlegi hiany: a Responses provider loaded_model_instance_ids metodusa ures listat ad, smoke_check alatt a loaded state ertekek None-ok. Ez provider-szinten eddig korrekt volt, de a kozponti app-viselkedeshez szukseg lehet egy kozos, LM Studio native katalogusra epulo loaded-model allapotfigyelesre akkor is, ha a chat provider Responses.

### Routerek

backend/app/routers/lm_studio.py jelenleg publikus endpointokat ad:

- GET /api/lm-studio/health,
- GET /api/lm-studio/models,
- POST /api/lm-studio/select-chat-model,
- POST /api/lm-studio/load-chat-model,
- POST /api/lm-studio/unload-chat-model,
- POST /api/lm-studio/chat.

A select-chat-model, load-chat-model es unload-chat-model az uj termekdontes szerint nem kivanatos UI-flow.

Elso implementacios korben a load, unload es select endpointok lehetnek deprecated vagy 410 Gone jelleggel letiltottak. A UI-bol mindenkeppen ki kell kerulniuk.

### Assistant service

backend/app/assistant_service.py a chat modelt jelenleg a runtime selected-model allapotbol veszi:

- streaming prepare alatt get_selected_chat_model(settings) adja a PreparedAssistantStream.model erteket,
- non-stream complete alatt provider.chat_completion szinten is get_selected_chat_model(settings) adja a modelt.

Ezt at kell allitani egy explicit, tiszta modellfeloldasra.

### Frontend

frontend/src/hooks/useModelState.ts jelenleg:

- health es model lista frissites,
- selected model state,
- select endpoint hivas,
- load endpoint hivas,
- unload endpoint hivas,
- success notice-ok: Kivalasztva, Betoltve, Levalasztva.

frontend/src/components/ModelPanel.tsx jelenleg tartalmazza:

- modellvalaszto select,
- Frissites,
- Betoltes,
- Levalasztas,
- tema gomb,
- status, notice es chat title.

Az uj celmodellben a select, load es unload UI el kell tunjon. Maradjon egy modellallapot-visszajelzo es Frissites/tema.

frontend/src/utils/notices.ts jelenlegi composer warningja:

Valassz ki es tolts be egy chat modellt az uzenetkuldeshez.

Ez az uj modellben pontositando, mert az appban mar nem lesz kivalasztas vagy betoltes.

## Uj modellfeloldasi szabaly

A chatkuldeshez hasznalt modell meghatarozasa legyen determinisztikus es mellekhatasmentes.

Javasolt szigoru szabaly:

1. A rendszer lekerdezi az LM Studio aktualis modellkatalogusat es loaded instance listajat.
2. Chathez a konfiguralt lm_studio_chat_model kell betoltve legyen.
3. Ha a konfiguralt modell betoltott, azt hasznaljuk.
4. Ha nincs betoltott modell, hiba.
5. Ha mas modell van betoltve, de a konfiguralt modell nincs, hiba.
6. Ha tobb modell van betoltve, de a konfiguralt modell nincs koztuk, hiba.

Ez a legtisztabb es a legkevesbe meglepo megoldas. Az app nem talalgat, nem valaszt automatikusan es nem tolt be semmit.

## Szükséges backend atalakitas

### F1 - Modellallapot-feloldo helper

Letre kell hozni egy belso helper vagy szolgaltatas logikat, amely providerfuggetlenul megmondja:

- LM Studio elerheto-e,
- konfiguralt modell elerheto-e,
- konfiguralt modell betoltott-e,
- melyik model id kuldheto chatre,
- ha nincs kuldheto modell, mi a felhasznalobarat hiba.

Fontos: Responses provider eseten is lehet a native /api/v1/models katalogust hasznalni allapotfigyelesre, mert az LM Studio futtatja a modelleket. Ez nem modellmenedzsment, csak allapotlekerdezes.

### F2 - Native auto-load kivezetese

A native provider chat_completion es chat_completion_stream metodusaibol ki kell venni az automatikus ensure_chat_model_loaded hivasat.

Helyette:

- a provider validalja, hogy a kapott model id nem ures,
- a chat payloadot az explicit model id-vel kuldi,
- ha LM Studio hibat ad, azt provider errorra forditja.

A modell betoltottsegi ellenorzes lehet a provider elott, assistant-service szinten, hogy a user hiba szebb legyen.

### F3 - Assistant service modellfeloldas

A get_selected_chat_model(settings) hasznalatot ki kell valtani.

A service kuldes, regenerate es retry prepare lepesben:

- meghivja a modellfeloldo helpert,
- ha nincs hasznalhato modell, dedikalt AssistantModelNotLoadedError vagy hasonlo hiba dobodik,
- ha van hasznalhato modell, a PreparedAssistantStream.model ezt kapja,
- non-stream complete ugyanezt hasznalja.

Router HTTP mapping javaslat:

- 409 Conflict, mert a keres ervenyes, de a runtime allapot nem alkalmas.

### F4 - Public model-management endpointok kivezetese

Endpoint dontes:

- GET /health es GET /models maradjon,
- POST /select-chat-model kivezetendo,
- POST /load-chat-model kivezetendo,
- POST /unload-chat-model kivezetendo.

Elso korben biztonsagosabb lehet:

- endpointok megmaradnak, de 410 Gone ertheto hibaval ternek vissza,
- frontend mar nem hivja oket,
- kesobb fizikai torles.

Javasolt detail:

Model lifecycle is managed in LM Studio. This app no longer loads or unloads models.

### F5 - Provider Protocol tisztitas

A LLMProvider Protocol jelenleg modellmenedzsment metodusokat is tartalmaz.

Ket lehetoseg:

1. Elso implementacios korben bent maradnak legacy metoduskent, de az app flow nem hasznalja oket.
2. Kesobbi takaritasban szetvalasztjuk inference provider es model state provider szerepekre.

Javaslat: ne bolygassuk tul nagyot elso korben. A Protocol takaritas lehet masodik lepes, miutan a termekviselkedes stabil.

## Szükséges frontend atalakitas

### F6 - useModelState egyszerusitese

useModelState maradjon allapotfigyelo hook:

- health lekerdezes,
- models lekerdezes,
- loaded state lekerdezes,
- refresh,
- notice.

Kikerul:

- handleSelectModel,
- handleLoadModel,
- handleUnloadModel,
- selected model mutacio,
- isModelBusy, ha mar csak refresh van, vagy atnevezheto isRefreshingModelState ertekre.

A hook ne tartson sajat selected model state-et, ha azt nem lehet UI-bol modositani. A kijelzett model legyen backend health/model response-bol szarmaztatva.

### F7 - ModelPanel egyszerusitese

Kikerul:

- select,
- Betoltes,
- Levalasztas.

Marad:

- Modell allapot,
- konfiguralt vagy hasznalt modell neve,
- loaded status,
- notice sor,
- Frissites,
- tema gomb,
- chat title.

A panel szovege legyen egyertelmu:

- Betoltve, ha a konfiguralt es hasznalhato modell betoltott,
- Nincs betoltve, ha nincs hasznalhato betoltott modell,
- Nem elerheto, ha LM Studio nem elerheto.

### F8 - Composer warning finomitas

A warning ne mondja, hogy valassz es tolts be modellt az appban.

Javasolt szoveg:

Az alkalmazasban beallitott chat modell nincs betoltve az LM Studio-ban.

## Tesztelesi terv

Backend unit:

- native provider chat nem hivja a /api/v1/models/load endpointot,
- native provider stream chat nem hivja a /api/v1/models/load endpointot,
- auto-load config kivezetes vagy figyelmen kivul hagyas tesztelve,
- assistant service hibat dob, ha nincs betoltott konfiguralt modell,
- assistant service a konfiguralt betoltott modellt hasznalja,
- router send es stream 409-et ad, ha nincs betoltott modell,
- select, load es unload endpointok deprecated vagy 410 viselkedese tesztelve, ha ezt valasztjuk.

Frontend:

- build,
- ModelPanel mar nem renderel select, load es unload elemeket,
- Frissites marad,
- composer warning uj szoveggel jelenik meg, ha nincs betoltott modell,
- send gomb es enter kuldes tovabbra is blokkolt, ha nincs betoltott modell.

Manual smoke:

1. LM Studio fut, nincs modell betoltve: app status Nincs betoltve, kuldes nem engedett vagy backend 409.
2. LM Studio-ban betoltjuk a konfiguralt 9B modellt: app Frissites utan Betoltve, kuldes mukodik.
3. Mas modell van betoltve, konfiguralt nincs: app nem talalgat, hibat jelez.
4. Native providerrel normal chat es stream mukodik.
5. Responses providerrel normal chat es stream mukodik.
6. Responses providerrel Excel es Obsidian tool mode tovabbra is mukodik.

## Kockazatok

- Ha LM Studio tobb modellt tart betoltve, a szigoru konfiguralt-modell szabaly elsore kenyelmetlenebb lehet, de csokkenti a meglepetest.
- A UI egyszerusites utan a felhasznalo csak LM Studio-ban tud modellt valtani; ez tudatos termekdontes.
- A backend endpointok 410-re allitasa torheti az esetleges kulso kliens hasznalatot, de jelenleg ezek belso app endpointok.
- Responses provider loaded-state figyeleset native katalogusbol kell megoldani, kulonben a UI nem tud egységesen allapotot mutatni.

## Lezarasi feltetel

A terv akkor tekintheto kesznek, ha:

- az app sem native, sem Responses uton nem vegez rejtett modellbetoltest chatkuldes kozben,
- a UI-bol eltunt a modellvalaszto, Betoltes es Levalasztas,
- az app csak allapotot jelez es Frissitest enged,
- kuldes csak betoltott konfiguralt modell mellett tortenik,
- native es Responses provider smoke is mukodik,
- a default provider tovabbra is lm_studio_native, de a viselkedes mar Responses-kompatibilis.
