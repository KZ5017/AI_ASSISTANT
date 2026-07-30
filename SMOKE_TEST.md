# Local Smoke Test

A backend es frontend WSL2 Ubuntu alatt fut. Az LM Studio a Windows hoston fusson, Local Server bekapcsolva.

## Env fajlok

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Ellenorizd:

- `AI_ASSISTANT_DATABASE_URL`
- `AI_ASSISTANT_LM_STUDIO_BASE_URL`
- `AI_ASSISTANT_LM_STUDIO_CHAT_MODEL`
- `AI_ASSISTANT_CONTEXT_CHAR_BUDGET`
- `AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID`
- `AI_ASSISTANT_LM_STUDIO_API_TOKEN`, ha LM Studio authentication aktiv
- AI_ASSISTANT_GRAPHRAG_BASE_URL
- AI_ASSISTANT_GRAPHRAG_SERVICE_TOKEN
- AI_ASSISTANT_GRAPHRAG_REQUEST_TIMEOUT_SECONDS
- AI_ASSISTANT_GRAPHRAG_RESULT_LIMIT
- AI_ASSISTANT_GRAPHRAG_CONTEXT_CHAR_BUDGET
- AI_ASSISTANT_GRAPHRAG_MAX_RESPONSE_BYTES
- AI_ASSISTANT_GRAPHRAG_VAULT_ID, ha egy konkrét vaultot kell rögzíteni
- `VITE_API_BASE_URL`

Jelenlegi standalone Postgres host port: `56000`.

## PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

Alap adatbazis:

- DB: `ai_assistant`
- User: `ai_assistant`
- Password: `ai_assistant`
- Host URL: `localhost:56000`

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Masik terminalbol:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/assistant/status
curl http://localhost:8000/api/assistant/chats
curl -X POST http://localhost:8000/api/assistant/chats -H "Content-Type: application/json" -d '{}'
```

## LM Studio

```bash
curl http://localhost:8000/api/lm-studio/health
curl http://localhost:8000/api/lm-studio/models
```

A modell betolteset es levalasztasat az LM Studio-ban kell vegezni. Az app regi select/load/unload endpointjai legacy modban 410 Gone valaszt adnak.

## Obsidian / Tudásbázis smoke

Elokeszites:

1. LM Studio 0.4.0 vagy ujabb fusson.
2. Az Obsidian MCP server mukodjon az LM Studio sajat chat feluleten.
3. Az LM Studio server settingsben legyen engedelyezve az mcp.json szerverek API-bol torteno hivasa.
4. Ha LM Studio authentication aktiv, a backend `.env` tartalmazza az `AI_ASSISTANT_LM_STUDIO_API_TOKEN` erteket.
5. A backend `.env` tartalmazza vagy defaultbol hasznalja: `AI_ASSISTANT_LM_STUDIO_OBSIDIAN_INTEGRATION_ID=mcp/obsidian`.

Manual smoke:

- Normal modban a Tudásbázis gomb legyen kikapcsolva.
- Tudásbázis modban a gomb legyen bekapcsolva.
- Ugyanazzal a vault-alapu prompttal a Tudásbázis mod ne mondja azt, hogy nincs hozzaferese a vaulthoz, hanem a `00-INDEX.md` menten keressen es vault-alapu valaszt adjon.
- App-hasznalati vagy modulkerdesnel ne altalanos Obsidian/MCP funkciokat magyarazzon, hanem a vault app-dokumentacios jegyzeteibol valaszoljon.

Aktualis manual status: a felhasznalo LM Studio authentication + Obsidian MCP mellett kiprobalta, es a Tudásbázis mod vault-alapu valaszadasa mukodik. A prompt legutobb magyar, Excel-prompt mintaju vault-only policy-ra lett szigoritva, hogy reasoning nelkul se csusszon at altalanos Obsidian/MCP leirasba.

## Responses / Eszközhasználat smoke

Elokeszites:

1. A backend `.env` allitsa a providert `lm_studio_responses` ertekre, ha a Responses utat teszteled.
2. Az LM Studio-ban a konfiguralt `qwen/qwen3.5-9b` modell legyen betoltve.
3. Excel MCP esetén a remote MCP endpoint legyen elerheto: `http://127.0.0.1:8017/mcp`.
4. Obsidian MCP esetén a remote MCP URL es Bearer token lokalis `.env`-ben legyen beallitva.

Manual smoke:

- Normal chat tool nelkul: nincs `Eszközhasználat` doboz.
- Adatbázis/Excel mod: megjelenik az `Eszközhasználat` doboz, a vegleges valasz kulon epul.
- A doboz tartalma gazdagitott, listás Markdown: tool nev, fajl, munkalap, keresesi/szuresi/osszefoglalasi reszlet es talalatszam, ha elerheto.
- Mentett valasz ujranyitasakor az `Eszközhasználat` disclosure alapbol csukott, lenyithato, es nem resze a kovetkezo modellkontextusnak.
- Tudásbázis/Obsidian és Adatbázis/Excel módban a Gondolkodó kapcsoló letiltott, és nincs `Gondolatmenet` artifact; az `Eszközhasználat` doboz ettől függetlenül megjelenhet.

## GraphRAG smoke

Előkészítés:

1. A külön /home/bober/projects/graphrag_system runtime legyen elindítva, és a http://127.0.0.1:8080/ready adjon ready választ.
2. Az Assistant backend .env fájljában az AI_ASSISTANT_GRAPHRAG_BASE_URL és AI_ASSISTANT_GRAPHRAG_SERVICE_TOKEN egyezzen a GraphRAG szolgáltatással.
3. Az LM Studio-ban a konfigurált qwen/qwen3.5-9b modell legyen betöltve az evidence-ből készülő végső válaszhoz.

Manual smoke:

- A GraphRAG módot kizárólag a felhasználói kapcsoló aktiválja; a kérdés tartalma nem választ módot.
- Tudásbázis, Adatbázis és GraphRAG egyszerre csak egy aktív forrásmód lehet; Gondolkodó csak Normál és GraphRAG módban használható.
- Releváns kérdésnél a backend friss retrievalt végez, a válasz Sx hivatkozásokat használ, és a csukott Források panel biztonságos provenance-t mutat.
- Ugyanazon kérdés retry és regenerate művelete is új retrievalt indít.
- No-evidence esetén rövid, determinisztikus válasz érkezik, modellhívás nélkül.
- A GraphRAG leállításakor a GraphRAG kérés 503-at ad, nincs silent fallback; normál, Tudásbázis és Adatbázis mód továbbra is használható.
- A böngészőben, API válaszban, mentett üzenetben és logban ne jelenjen meg service token, nyers GraphRAG válasz vagy teljes evidence.

Automatikus coverage: backend/tests/test_graphrag_mode.py ellenőrzi a fix retrieve kérést, Bearer headert, timeout/auth/contract/méret hibákat, evidence rendezést és költségkeretet, no-evidence ágat, send/retry/regenerate friss retrievalt, normál mód izolációját és biztonságos provenance-t.

## Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Nyisd meg Windowsbol: http://localhost:5173

## Manual smoke

1. App betolt Windows bongeszoben.
2. Modell panelben LM Studio allapot latszik.
3. Modelllista frissitheto.
4. Chat modell valaszthato.
5. Modell betoltheto.
6. Uj chat letrehozhato.
7. Uzenet kuldheto normal modban, az assistant valasz streaminggel epul fel.
8. Gondolkodo bekapcsolhato, ikon valt `LightbulbOff` -> `Lightbulb`.
9. Assistant valasz Markdownkent renderelodik.
10. Assistant valasz masolhato.
11. Csak a legutolso assistant valasz ujrageneralhato, es az uj valasz streaminggel epul fel.
12. Chat atnevezheto.
13. Chat törlése alapból végleges; soft delete csak explicit konfigurációs átállítás mellett használható.
14. Hosszu prompt/context warning a composer alatt stabil slotban jelenik meg, layout ugralas nelkul.
15. Light/dark tema valthato.
16. Betoltott modell levalaszthato; kuldes tiltott, ha nincs betoltve modell.
17. Streaming kozben a pending assistant buborek latszik, majd done utan frissites utan is megmarad a vegleges assistant valasz.
18. Streaming kozben a composer gomb Leallitas allapotba valt, abort utan nem jelenik meg hibakent a stop.
19. Normal send stop utan az utolso user uzenet alatt megjelenik a Szerkesztes es Ujrakuldes recovery action.
20. Ujrakuldes nem duplikalja a user uzenetet, hanem arra streamel assistant valaszt.
21. Szerkeszteskor a user bubble textarea automatikusan lefele no, nincs manualis resize fogantyu, es csak fuggoleges scrollbar jelenhet meg.
22. Mentes es kuldes a modositott user szovegre indit streamelt assistant valaszt.
23. Gondolkodo modban uj uzenet utan a live `Gondolkodik` / `Gondolatmenet` panel latszik stream kozben.
24. A vegleges assistant valasz felett megjelenik a mentett, alapbol csukott `Gondolatmenet` disclosure, ha a modell kuldott reasoninget.
25. Mentett reasoning disclosure lenyithato, Markdownkent renderel, de a kovetkezo prompt contextjebe nem kerul vissza.
26. Tudásbázis/Obsidian mod bekapcsolhato, tooltipje allapotfuggo, es LM Studio MCP integration mellett `00-INDEX.md`-bol indulva, vault-jegyzetek alapjan valaszt ad.
27. Markdown layout hygiene: hosszu code block es GFM tablazat nem fesziti szet a chat savot; inline code jelenlegi viselkedese elfogadott.
28. Adatbázis/Excel modban a letisztitott prompttal a modell `00-INDEX.xlsx`-bol indul, celzott read-only Excel toolokat hasznal, es forrasfajl/munkalap/oszlop megjelolessel ad valaszt.
29. A GraphRAG gomb külön kapcsolható, a Tudásbázis és Adatbázis móddal kölcsönösen kizáró, a Gondolkodóval kombinálható. Tudásbázis vagy Adatbázis aktiválásakor a Gondolkodó automatikusan kikapcsol és a gomb `not-allowed` kurzorral letiltott marad; a backend API is `normal` reasoningra kényszeríti ezt a kombinációt.
30. GraphRAG módban releváns kérdésnél Sx hivatkozásos válasz és csukott Források panel jelenik meg.
31. A forráspanel csak biztonságos fájlútvonalat/címsort, típust és obsidian linket mutat; tokent, raw response-t vagy teljes evidence-et nem.
32. Nem releváns kérdésnél is kötelezően a GraphRAG retrieve út fut; nincs automatikus normál-chat routing.
33. No-evidence válasznál determinisztikus magyar válasz érkezik LLM-hívás nélkül.
34. Retry és regenerate új GraphRAG retrievalt indít, nem használ korábban mentett evidence-et.
35. GraphRAG szolgáltatás kiesésekor a GraphRAG mód 503-at ad silent fallback nélkül, miközben a normál és MCP módok működőképesek maradnak.

Mentett reasoning disclosure DB smoke:

```bash
docker compose exec -T postgres psql -U ai_assistant -d ai_assistant -c "\d assistant_messages"
```

Az `assistant_messages` tablan legyen `reasoning_content` oszlop.

Legutóbbi kézi állapot: a normál streaming, recovery, reasoning, Tudásbázis/Obsidian, Adatbázis/Excel és Responses tool activity működött. Az explicit GraphRAG mód releváns, negatív, reasoninges és szolgáltatásfüggetlenségi live smoke-ja sikeres volt: GraphRAG kiesésnél a normál mód működött, a GraphRAG mód pedig 503-at adott silent fallback nélkül. A GraphRAG forráspanel csak biztonságos provenance-t mutatott.

## Automata ellenorzesek

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
ruff check app tests
```

Frontend:

```bash
cd frontend
npm run build
```
