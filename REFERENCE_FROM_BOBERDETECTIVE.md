# Reference Map From BoberDetective

This document lists which parts of BoberDetective are useful as reference for the standalone AI Assistant app.

The goal is not blind copying. The goal is to transfer proven decisions and avoid re-solving already solved issues.

## Backend reference files

### Assistant core



Use for:

- chat list/create/get/update/delete behavior,
- send message flow,
- regenerate latest assistant answer,
- context budget guard,
- minimal system prompt,
- reasoning mapping,
- auto-title logic,
- error classes.

Do not copy BoberDetective imports blindly. Replace app-specific DB/session/config imports with standalone equivalents.

### API routes



Use for:

- endpoint shapes,
- response models,
- HTTP error mapping,
- context-limit structured error.

### Schemas



Use nearly directly:

- request/response schema names,
- ,
-  max length 120000,
- .

### Models



Use for table design.

Standalone adjustment:

- omit  unless user accounts are intentionally added.

### Migration



Use for SQL/Alembic table structure.

Standalone adjustment:

- remove FK to  if no users table.

### LLM provider



Only use:

- ,
- ,
- ,
- LM Studio native model listing/loading/unloading,
- ,
- ,
- ,
- ,
- .

Do not copy:

- embedding support,
- Qdrant-oriented logic,
- benchmark-only parts unless wanted.

### Config



Use for:

- dataclass settings style,
- env helper pattern,
- LM Studio settings.

Standalone adjustment:

- rename env vars from  to neutral names, e.g. .

## Frontend reference files

### API client



Use only assistant-related types and functions.

Search terms:



### App behavior



Use only assistant-related logic:

- state variables around ,
- ,
- ,
- ,
- ,
- rename dialog handlers,
- context limit helpers,
- copy/regenerate handlers,
- send handler,
- render assistant message,
- render pending user,
- render typing,
- render assistant surface.

Do not copy the whole App.tsx. It is a workbench monolith and includes many unrelated modules.

### Styles



Use as visual reference for:

- CSS tokens,
- assistant shell,
- history rail,
- context menu popover,
- rename dialog,
- chat canvas,
- message bubbles,
- composer,
- message actions,
- reasoning toggle,
- global scrollbar,
- dark mode tokens.

Recommended approach:

- re-create a smaller token system,
- port assistant styles deliberately,
- avoid importing the whole BoberDetective stylesheet.

## Documentation reference



Use for product decisions and reasoning.

## Known good values



Model quality profile:



Speed fallback:



## Known solved UX details

Keep these decisions:

- Enter inserts newline, it does not send.
- Send happens through icon button.
- Pending user message appears immediately.
- Typing indicator appears while backend waits.
- Regenerate only latest assistant message.
- Regenerate is guarded against repeated clicks.
- Copy is frontend-only.
- Rename uses custom dialog, not native prompt.
- Delete uses custom dialog, not native confirm.
- Conversation menu closes on outside click and Escape.
- Too-long prompt warning has its own composer grid row.
- Composer focus feedback must not cause pixel jump.
- User bubble max height around 15 lines with internal scrollbar.
- Assistant answer renders Markdown safely.
- No streaming in first baseline.

## Important traps to avoid

- Do not silently truncate chat history.
- Do not let old BoberDetective modules leak into dependencies.
- Do not use browser-native prompt/confirm for core UI.
- Do not make reasoning default-on.
- Do not hardcode BoberDetective colors/brand names.
- Do not build RAG or document upload into the first version.
- Do not put all frontend state into a giant future-unmaintainable App.tsx if avoidable.

