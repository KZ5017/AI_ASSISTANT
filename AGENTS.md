# AGENTS.md - Standalone AI Assistant App

## Project Goal

Build a fully standalone local AI chat web application inspired by the AI-asszisztens module already implemented in BoberDetective.

The app must be generic. It must not be investigative, source-bound, RAG-based, case-aware, or BoberDetective-branded.

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
- Qdrant,
- embeddings,
- RAG,
- source references,
- claims,
- entities,
- events,
- contradiction candidates,
- audit/provenance graph,
- investigative prompts,
-  behavior.

This app is a normal local AI chat interface. If a user pastes document text into the chat, it is just chat input.

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

