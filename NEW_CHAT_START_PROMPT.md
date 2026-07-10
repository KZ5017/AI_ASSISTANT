# New Chat Start Prompt

Masold ezt egy uj Codex chat elejere, ha ezt a standalone AI Assistant projektet szeretned folytatni.

--- PROMPT START ---

A `/home/bober/projects/AI_Assistant` projektben egy standalone, lokalis LM Studio chat webappot epitunk.

Kerlek eloszor olvasd el az aktualis allapotfajlokat:

/home/bober/projects/AI_Assistant/README.md
/home/bober/projects/AI_Assistant/AGENTS.md
/home/bober/projects/AI_Assistant/STANDALONE_AI_ASSISTANT_HANDOFF.md
/home/bober/projects/AI_Assistant/IMPLEMENTATION_PLAN.md
/home/bober/projects/AI_Assistant/SCAFFOLD.md
/home/bober/projects/AI_Assistant/SMOKE_TEST.md
/home/bober/projects/AI_Assistant/WINDOWS_START.md

Referencia projekt tovabbra is itt van, de csak mint torteneti/technikai referencia:

/home/bober/projects/Codex_BoberDetective

Fontos hatar:

- ne hozz be BoberDetective domain funkciokat,
- ne legyen case/document/RAG/Qdrant/source reference/OCR/Docling,
- ne legyen nyomozati objektum vagy audit/provenance workflow,
- ne legyen BoberDetective brand,
- ne epits BoberDetective adatbazisra.

A standalone app jelenlegi allapotban mar tartalmaz:

- FastAPI backendet,
- PostgreSQL + Alembic persistence-t,
- React/Vite/TypeScript frontendet,
- LM Studio health/list/select/load/unload/chat szerzodeseket,
- mentett beszelgeteseket,
- uj chat / rename / soft delete funkciokat,
- streamelt uzenetkuldes / Markdown / copy / streamelt latest regenerate funkciokat,
- stream leallitast, stop utani Ujrakuldes recovery flow-t es inline Szerkesztes + Mentes es kuldes flow-t,
- Gondolkodo kapcsolot,
- 120000 karakteres context guardot,
- light/dark tokenizalt UI-t,
- Windows PowerShell indito/status/stop scripteket.

Eloszor ne kodolj automatikusan. Eloszor foglald ossze, mit olvastal ki az aktualis allapotfajlokbol, milyen reszek vannak kesz, milyen reszek maradtak nyitva, es milyen kovetkezo lepes lenne logikus.

--- PROMPT END ---
