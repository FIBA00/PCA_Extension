---
description: "Use when editing backend Python code in PromptCrafter. Covers naming conventions, router/service boundaries, and migration expectations for FastAPI + SQLAlchemy changes."
name: "PromptCrafter Backend Guardrails"
applyTo: "backend/**"
---

# Backend Guardrails

## Scope

- Applies to files under `backend/**`.
- Keep changes minimal and aligned with existing FastAPI + SQLAlchemy patterns.

## Naming Rules

- Use clear snake_case for Python modules, functions, and variables.
- Keep API route handlers descriptive and action-based (for example: `create_prompt`, `get_user_prompts`).
- Prefer explicit service function names over generic names (avoid `process`, `handle`, `do_stuff`).

## Router and Service Boundaries

- Put HTTP concerns in routers (`backend/routers/**`): request/response models, status codes, auth dependencies.
- Put business logic in services (`backend/services/**`): prompt generation rules, user domain actions, orchestration.
- Keep database persistence logic in service/data layers, not directly embedded in route handlers.
- When adding new endpoints, follow the existing split used by:
    - `backend/routers/prompt.py` + `backend/services/prompt_service.py`
    - `backend/routers/user.py` + `backend/services/user_service.py`

## Schema and Model Changes

- If SQLAlchemy models change in `backend/db/models.py`, add/update an Alembic migration in `backend/migrations/versions/`.
- Keep migrations reversible whenever possible.
- Avoid mixing unrelated schema changes in one migration.
- Ensure runtime code and migration changes ship together in the same PR.

## Migration Expectations

- Use `uv` commands for backend workflows.
- Validate migration chain before finishing:
    - `cd backend && uv run alembic upgrade head`
- If a migration affects prompt/user flows, run targeted tests:
    - `cd backend && uv run pytest tests/test_prompt_routes.py tests/test_user_routes.py`

## Testing Expectations

- For router/service edits, run the closest test file first.
- Run full backend suite (`cd backend && uv run pytest`) when changes touch shared core paths such as `backend/main.py`, `backend/core/**`, or cross-cutting auth/db wiring.

## Dependency and Style Discipline

- Do not introduce new Python dependencies unless explicitly required by the task.
- Prefer straightforward functions and readable flow over new abstractions.
- Preserve existing public API behavior unless the task explicitly requests a behavior change.
