# New Chat Start Prompt

Másold ezt egy új Codex chat elejére, ha a standalone AI Assistant projektet szeretnéd folytatni.

--- PROMPT START ---

A /home/bober/projects/AI_Assistant repóban egy standalone, lokális LM Studio chat webappot építünk.

Mielőtt bármit módosítasz, olvasd el teljesen:

- /home/bober/projects/AI_Assistant/AGENTS.md
- /home/bober/projects/AI_Assistant/README.md
- /home/bober/projects/AI_Assistant/STANDALONE_AI_ASSISTANT_HANDOFF.md
- /home/bober/projects/AI_Assistant/implementation_plans/019_graphrag_mode_integration_plan.md
- /home/bober/projects/AI_Assistant/SMOKE_TEST.md
- /home/bober/projects/AI_Assistant/WINDOWS_START.md

Ezután nézd meg a git statust, a legutóbbi commitokat, az Alembic headet és a futó komponensek health állapotát. Ellenőrizd, hogy a backend és frontend .env létezik-e, de az értékeiket ne jelenítsd meg.

A /home/bober/projects/graphrag_system külön, külső rendszer. Csak akkor olvasd referenciaként, ha az Assistant és a publikus GraphRAG retrieval szerződés közötti határt kell ellenőrizni. Az Assistant nem férhet hozzá közvetlenül a GraphRAG adatbázisaihoz, projekcióihoz, vaultjához vagy belső Python moduljaihoz. A /home/bober/projects/Codex_BoberDetective kizárólag történeti referencia, nem módosítható ebből a projektből.

Az Assistant jelenlegi fő képességei:

- FastAPI backend, PostgreSQL és Alembic persistence;
- React/Vite/TypeScript frontend;
- LM Studio native és Responses provider utak, jelenleg qwen/qwen3.5-9b modellel;
- streaming chat, stop/retry/edit/regenerate, reasoning és mentett UI-only artifactok;
- explicit, egymást kizáró Tudásbázis/Obsidian, Adatbázis/Excel és GraphRAG forrásmód;
- a Gondolkodó kapcsoló mindhárom forrásmóddal kombinálható;
- 120000 karakteres context guard;
- Windows PowerShell start/status/stop scriptek.

GraphRAG módban kizárólag a felhasználó kapcsolója dönt a routingról. A backend minden send, retry és regenerate esetén friss, Bearer tokennel hitelesített POST /v1/retrieve hívást végez, szigorúan validálja a választ, rendezett Sx evidence blokkokat készít, és csak biztonságos provenance-t ment. Nincs közvetlen tárolóhozzáférés, automatikus módválasztás, silent fallback vagy nyers GraphRAG válasz perzisztálása. No-evidence esetén az LLM nem fut. A kliens jelenleg egyetlen próbálkozást végez explicit timeouttal; automatikus retry nincs.

A három forrásmód kölcsönösen kizárja egymást, de a normál chat és a többi mód GraphRAG kiesésekor is működőképes marad. A két repó runtime-jának egymástól függetlenül indíthatónak és leállíthatónak kell maradnia.

Legutóbbi rögzített ellenőrzési alapállapot: backend 80 teszt passed, ruff passed, frontend build passed, a GraphRAG pozitív, negatív, reasoninges és szolgáltatásfüggetlenségi live smoke-ja sikeres.

A következő logikus munka a két repó retrieval contractjának verziózott rögzítése és automatizált contract tesztje, majd a reasoning nélküli relevancia/negatív értékelési korpusz bővítése. Retry policy csak külön döntés és tesztelés után kerüljön a kliensbe.

Ne kezdj automatikusan kódolni: először foglald össze a kiolvasott aktuális állapotot, a repo saját módosításait, a nyitott kockázatokat és a javasolt következő lépést.

--- PROMPT END ---
