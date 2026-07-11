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
- `VITE_API_BASE_URL`

Jelenlegi standalone Postgres host port: `55432`.

## PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

Alap adatbazis:

- DB: `ai_assistant`
- User: `ai_assistant`
- Password: `ai_assistant`
- Host URL: `localhost:55432`

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
curl -X POST http://localhost:8000/api/lm-studio/select-chat-model -H "Content-Type: application/json" -d '{"model_id":"qwen/qwen3.6-35b-a3b"}'
curl -X POST http://localhost:8000/api/lm-studio/load-chat-model -H "Content-Type: application/json" -d '{"model_id":"qwen/qwen3.6-35b-a3b"}'
```

Levalasztas:

```bash
curl -X POST http://localhost:8000/api/lm-studio/unload-chat-model -H "Content-Type: application/json" -d '{"model_id":"qwen/qwen3.6-35b-a3b"}'
```

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
13. Chat soft delete mukodik.
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

Mentett reasoning disclosure DB smoke:

```bash
docker compose exec -T postgres psql -U ai_assistant -d ai_assistant -c "\d assistant_messages"
```

Az `assistant_messages` tablan legyen `reasoning_content` oszlop.

Legutobbi kezi allapot: a felhasznalo Windows bongeszobol kiprobalta a streaminget, a stop utani Ujrakuldes flow-t, az inline Szerkesztes flow-t, a recovery textarea finomitasokat, a reasoning panel scroll override-ot es a mentett reasoning disclosure-t; mukodonek es jonak jelezte.

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
