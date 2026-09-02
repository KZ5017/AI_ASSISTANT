# New Chat Start Prompt

Másold ezt egy új Codex chat elejére, ha a standalone AI Assistant projektet szeretnéd folytatni.

--- PROMPT START ---

A /home/bober/projects/AI_Assistant repóban egy standalone, lokális LM Studio chat webappot építünk.

Mielőtt bármit módosítasz, olvasd el teljesen:

- /home/bober/projects/AI_Assistant/AGENTS.md
- /home/bober/projects/AI_Assistant/README.md
- /home/bober/projects/AI_Assistant/system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md
- /home/bober/projects/AI_Assistant/STANDALONE_AI_ASSISTANT_HANDOFF.md
- /home/bober/projects/AI_Assistant/implementation_plans/019_graphrag_mode_integration_plan.md
- /home/bober/projects/AI_Assistant/SMOKE_TEST.md
- /home/bober/projects/AI_Assistant/WINDOWS_START.md

Ezután nézd meg a git statust, a legutóbbi commitokat, az Alembic headet és a futó komponensek health állapotát. Ellenőrizd, hogy a backend és frontend .env létezik-e, de az értékeiket ne jelenítsd meg.

A /home/bober/projects/graphrag_system külön, külső rendszer. Csak akkor olvasd referenciaként, ha az Assistant és a publikus GraphRAG retrieval szerződés közötti határt kell ellenőrizni. Az Assistant nem férhet hozzá közvetlenül a GraphRAG adatbázisaihoz, projekcióihoz, vaultjához vagy belső Python moduljaihoz. A /home/bober/projects/Codex_BoberDetective kizárólag történeti referencia, nem módosítható ebből a projektből.

Az Assistant jelenlegi fő képességei:

- FastAPI backend, PostgreSQL és Alembic persistence;
- React/Vite/TypeScript frontend;
- LM Studio native és Responses provider utak; a helyi aktív profil jelenleg
  qwen/qwen3.6-35b-a3b, a megőrzött alternatíva qwen/qwen3.5-9b;
- streaming chat, stop/retry/edit/regenerate, reasoning és mentett UI-only artifactok;
- explicit, egymást kizáró Tudásbázis/Obsidian, Adatbázis/Excel és GraphRAG forrásmód;
- két visszakapcsolható MCP-végrehajtási profil: `lmstudio_registered` az LM Studio
  `mcp.json` pluginjaihoz és `responses_remote` a korábbi dinamikus remote MCP úthoz;
- a Gondolkodó kapcsoló csak Normál és GraphRAG módban kombinálható;
- modellprofilhoz kötött context guard; az aktív qwen3.6 profilnál 30000 karakter;
- a chat UI legutóbbi finomítása: visszafogott aktív beszélgetés-sor, keretes
  user buborék és kódblokk, valamint a lenyitható artifact-panelek saját
  elválasztószínével egyező külső keret;
- a user buborék scrollozható tartalma külső margóval védett a kerettől; a fő
  asszisztensválaszok kódblokkjai belső toolbaros másolásgombot, sikeres másolás
  után pipa-visszajelzést és a lekerekített külső kereten belüli vízszintes
  scrollt kapnak. Ez a viselkedés szándékosan nem terjed ki az artifact-panelekre;
- az oldalsávban `Keresés...` mezővel élő, kis- és ékezetfüggetlen chatcím-szűrés
  van; a szűrő, composer és átnevezési input azonos fókuszkeretet kap, míg a
  globális futási/biztonsági warning banner megtartott halvány háttere mellett
  külső keret nélkül jelenik meg;
- a fő asszisztens-kódblokk külső lekerekítése `--radius-lg` (12px); sötét
  témában az inputok és a user buborék az alap `--color-surface`, a kódblokk
  `--color-surface-soft`, a beszélgetésmenü `--color-page` hátteret használja.
  Szerkesztő módban a user buborék kerete csak a belső textarea fókuszában lila.
  A sötét page/surface/text tokenek rendre `#11161e`, `#1d222a` és `#cbd5e7`;
- Windows PowerShell start/status/stop scriptek.

GraphRAG módban kizárólag a felhasználó kapcsolója dönt a routingról. A backend minden send, retry és regenerate esetén friss, Bearer tokennel hitelesített POST /v1/retrieve hívást végez, szigorúan validálja a választ, rendezett Sx evidence blokkokat készít, és csak biztonságos provenance-t ment. Nincs közvetlen tárolóhozzáférés, automatikus módválasztás, silent fallback vagy nyers GraphRAG válasz perzisztálása. No-evidence esetén az LLM nem fut. A kliens jelenleg egyetlen próbálkozást végez explicit timeouttal; automatikus retry nincs.

A három forrásmód kölcsönösen kizárja egymást, de a normál chat és a többi mód GraphRAG kiesésekor is működőképes marad. A két repó runtime-jának egymástól függetlenül indíthatónak és leállíthatónak kell maradnia.

Legutóbbi teljes ellenőrzési alapállapot: backend pytest 126 passed, Ruff passed,
frontend build passed. Jelenleg 139 teszt gyűlik; a 2026-08-22-i MCP-záráskor
107 érintett backend teszt, Ruff és a frontend build sikeres volt. A teljes suite
helyben egy meglévő FastAPI TestClient tesztnél várakozik; ezt ne kezeld új MCP-
regresszióként bizonyíték nélkül. A `lmstudio_registered` Excel és Obsidian útja
qwen/qwen3.6-35b-a3b modellel, az Assistant saját streaming API-ján is sikeres
live smoke-ot kapott. A `responses_remote` ág és regressziós lefedése megmaradt.
Az utolsó, csak CSS-t érintő UI-polish frontend production buildje 2026-08-23-án
sikeres volt.
Az ezt követő kódblokk-másolás és scroll-layout frontend production buildje is
sikeres volt.

A következő logikus munka a két repó retrieval contractjának verziózott rögzítése és automatizált contract tesztje, majd a reasoning nélküli relevancia/negatív értékelési korpusz bővítése. Retry policy csak külön döntés és tesztelés után kerüljön a kliensbe.

Ne kezdj automatikusan kódolni: először foglald össze a kiolvasott aktuális állapotot, a repo saját módosításait, a nyitott kockázatokat és a javasolt következő lépést.

--- PROMPT END ---
