# AGENTS.md — Agent customization for PromptCrafter

Purpose: concise guidance for AI coding agents working in this repository. Keep edits minimal and link to project docs.

Quick facts
- **Language / runtime**: Python 3.12+ (backend), Node.js (frontend)
- **Backend**: FastAPI (backend/)
- **Package manager**: `uv` for Python projects (see backend/pyproject.toml)

Essential commands (use from repo root)

Backend (development)

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev main.py
```

Tests

```bash
cd backend
uv run pytest
```

Docker

```bash
docker-compose up -d
```

Where to look (high-value files)

- Project README: [README.md](README.md)
- Backend entry: [backend/main.py](backend/main.py#L1)
- Backend deps: [backend/pyproject.toml](backend/pyproject.toml#L1)
- Routers: [backend/routers](backend/routers)
- DB models: [backend/db/models.py](backend/db/models.py#L1)
- Migrations: [backend/migrations](backend/migrations)
- Backend tests: [backend/tests](backend/tests)
- Browser extension files: [extension](extension)

Conventions & guidance for agents
- Prefer linking to existing docs instead of copying them (see README.md and backend/README.md).
- Changes should be minimal, focused, and follow the repository style (small diffs, preserve APIs).
- If adding or updating runtime commands, ensure they work with `uv` and include migration steps when touching models or schema.
- When editing backend behavior, run the test subset that touches modified modules.

Focused test examples

```bash
cd backend
uv run pytest tests/test_prompt_routes.py
uv run pytest tests/test_user_routes.py
```

Common pitfalls
- `uv` is used as the local package/task runner — do not assume `pip` scripts in CI without verifying `pyproject.toml`.
- Local env: ensure `.env` is present and migrations applied before running the server.
- Node/npm paths: some dev environments may require loading `nvm` (see local dev notes).
- `backend/README.md` is currently empty; rely on root docs and source files for backend behavior.

Follow-ups (suggested agents/skills)
- A `backend-tests` skill to run focused pytest groups.
- A `create-agent` template for PR-checklist automation (run migrations, run tests, format).

Contact / maintainers
- Primary: repository owner (see README.md contact section)
