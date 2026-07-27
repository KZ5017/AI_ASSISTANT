# AGENTS.md - Standalone AI Assistant App

## Project Goal

Build a fully standalone local AI chat web application inspired by the AI-asszisztens module already implemented in BoberDetective.

The app remains generic and must not be investigative, case-aware, or BoberDetective-branded. It may consume the separate GraphRAG Knowledge Service only when the user explicitly selects GraphRAG mode.

Working name:



## Core Product Definition

A local web chat interface for LM Studio:

- saved conversations,
- new chat creation,
- chat rename,
- soft delete,
- user/assistant message history,
- Markdown-rendered assistant answers,
- copy assistant answer,
- regenerate latest assistant answer,
- reasoning toggle per send/regeneration,
- explicit context-window guard,
- light/dark tokenized UI,
- fully local backend and frontend.

## Hard Boundary

Do not import BoberDetective domain concepts into this app.

Do not include:

- cases,
- documents,
- OCR,
- Docling,
- events,
- contradiction candidates,
- audit/provenance graph,
- investigative prompts,
-  behavior.

This app is a normal local AI chat interface. If a user pastes document text into the chat, it is just chat input.

GraphRAG integration boundary:

- The Assistant does not implement or own a RAG pipeline.
- It must not access GraphRAG PostgreSQL, Qdrant, Neo4j, vault files, embeddings, extraction, or internal Python modules directly.
- It may call the GraphRAG Knowledge Service public read-only `/v1/retrieve` HTTP API.
- GraphRAG routing is controlled only by the explicit user mode switch, never by model intent classification.
- GraphRAG, Obsidian MCP, and Excel MCP remain mutually exclusive.
- Reasoning remains independently combinable with every source mode.
- GraphRAG failure must not affect normal, Obsidian, or Excel mode, and must never silently fall back to normal chat.
- Never log, persist, or expose the GraphRAG service token or raw retrieval response.

## Reference Source

The reference implementation lives in:



Read these BoberDetective files only as reference material:

- 
- 
- 
- 
-  only the LM Studio native chat/model-load parts
-  only LLM/config patterns
- 
- 
- 
-  assistant-related types/functions only
-  assistant-related state/functions/rendering only
-  assistant, token, dialog, popup, scrollbar, Markdown-related styles only
- 
- 

Do not copy the whole BoberDetective application.

## Preferred Stack

Backend:

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL for parity with the proven setup
- httpx
- pytest

Frontend:

- React
- Vite
- TypeScript
- lucide-react
- react-markdown
- remark-gfm

Runtime:

- Windows 11 host runs LM Studio
- WSL2 Ubuntu runs backend/frontend
- Backend talks to LM Studio through local native API / OpenAI-compatible API where appropriate

## UI Language

Use Hungarian UI labels if this is intended for the same user workflow.
Internal enum/API values may remain English.

## Development Style

Start design-first:

1. Scaffold minimal backend and frontend.
2. Implement LM Studio health/model-load/chat provider.
3. Implement assistant chat persistence.
4. Implement chat UI.
5. Add context guard and reasoning toggle.
6. Add copy/regenerate/rename/delete polish.
7. Add dark mode tokens.
8. Verify with tests and build.

Keep changes small and testable.


## Resume Protocol

At the start of a future session:

1. Read README.md, system_documentation/INTEGRATED_LOCAL_AI_SYSTEM.md, STANDALONE_AI_ASSISTANT_HANDOFF.md, implementation_plans/019_graphrag_mode_integration_plan.md, SMOKE_TEST.md, and WINDOWS_START.md.
2. Inspect git status, recent commits, and the Alembic head before editing.
3. Verify backend/.env and frontend/.env exist without displaying their values.
4. Check the Assistant health/status endpoints and confirm qwen/qwen3.5-9b is loaded in LM Studio. For GraphRAG-dependent work, also check the external GraphRAG /ready endpoint.
5. Run backend pytest and ruff checks plus the frontend production build before and after material changes.
6. Update STANDALONE_AI_ASSISTANT_HANDOFF.md whenever the migration head, test count, runtime contract, known limitation, or next step changes materially.

The next planned work is to version and automatically test the cross-repository retrieval contract, then expand the reasoning-off relevance evaluation corpus. Preserve explicit user routing, source-mode mutual exclusion, runtime independence, and the no-direct-storage-access boundary. Do not add automatic GraphRAG routing, silent fallback, retry behavior, or direct GraphRAG storage access without a separately reviewed plan.
