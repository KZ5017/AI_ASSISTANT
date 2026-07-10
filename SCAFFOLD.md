# Scaffold / Current Structure

Ez mar nem csak minimal scaffold: a standalone chat app alap backendje, frontendje, persistence retege es LM Studio modellkezelo felulete mukodik.

## Backend

Stack:

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- httpx
- pytest / ruff

Fontos modulok:

- `app/main.py` - FastAPI app, CORS, routerek.
- `app/config.py` - `AI_ASSISTANT_*` settings.
- `app/db.py` - SQLAlchemy engine/session/Base.
- `app/models.py` - assistant chat es message modellek.
- `app/schemas.py` - request/response schemak.
- `app/assistant_service.py` - chat create/list/get/rename/delete/send/regenerate logika.
- `app/llm_provider.py` - LM Studio native API provider.
- `app/model_runtime.py` - runtime selected chat model state.
- `app/routers/assistant.py` - assistant API.
- `app/routers/lm_studio.py` - LM Studio health/model/load/unload/chat API.
- `app/routers/health.py` - backend health.

## Frontend

Stack:

- React
- Vite
- TypeScript
- lucide-react
- react-markdown
- remark-gfm

Fontos fajlok:

- `src/api/assistant.ts` - assistant es LM Studio API client.
- `src/components/ChatShell.tsx` - fo chat UI.
- `src/styles/tokens.css` - light/dark tokenek.
- `src/styles/app.css` - layout, gombok, composer, model panel, message UI.

## Infrastructure

- `docker-compose.yml` csak standalone Postgres indit.
- Kontener: `ai-assistant-postgres`.
- Volume: `ai_assistant_postgres_data`.
- Host port: `55432`.
- Windows scriptek: `scripts/start.ps1`, `scripts/status.ps1`, `scripts/stop.ps1`.
- Elfogadott Windows inditas: egyszeru PowerShell script harom WSL paranccsal, ket 5 masodperces szunettel, kozvetlen `setsid -f` backend/frontend inditassal.

## Jelenlegi UI allapot

- Bal oldali conversation rail: uj chat, refresh, elvalasztott mentett chat lista.
- Mentett chat lista: alapbol csendes sorok, hoverre secondary gombtest, aktiv chat primary/narancs.
- Chat canvas: felso modell/status panel a chat cimmel es tema gombbal.
- Modell panel: modellvalaszto, Frissites, Betoltes, Levalasztas.
- Uzenetsav: kozepre koncentralt olvasosav, teljes szeles scroll container.
- Composer: also pozicio, autosize textarea, max magassag utan belso scroll; desktopon Enter kuld es Shift+Enter sortorest ad, mobilon kulon send gomb is van.
- A textarea felfele no ki a 40px-es composer slotbol, igy a composer sor magassaga stabilabb.
- Composer input: surface hatter, standard border, 18px radius, shadow nelkul.
- Warning slot: a textarea alatt allandoan fenntartott egysoros hely; uresen lathatatlan, warningnal stabilan megjelenik.
- Gondolkodo gomb: primary send-gomb csalad, inaktivan halvany, aktivan teljes primary, `LightbulbOff` / `Lightbulb` ikonnal.
- Secondary akciok: alapbol szoveges/ikonos, hoverre kapnak secondary gombtestet.
- Mobil nezet: a mobilos CSS egy kozos, fajl vegi max-width 760px media query blokkban van.

## Stabil inditasi szabaly

A `scripts/start.ps1` jelenlegi formaja szandekosan minimalis es mar Windowsbol tesztelt. Ne tegyunk vissza bele portproxy-t, belso `sh -c` reteget vagy start elotti `pkill` parancsot. A regi folyamatok leallitasa a `scripts/stop.ps1` feladata.

## Ismert kovetkezo jo lepesek

- UI smoke teszt kepernyomeretekkel, kulon light es dark modban.
- Backend es frontend tesztek rendszeres futtatasa.
- Opcionlisan: model panel hibauzenetek es warningok finomhangolasa.
- Opcionlisan: komponensbontas `ChatShell.tsx` meretenek csokkentesere.
