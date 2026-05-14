---
name: backend-tests
description: "Run targeted PromptCrafter backend tests based on touched files. Use for fast validation of routers, services, auth, db, and migrations without always running the full test suite."
argument-hint: "Optional git base ref (default: origin/main)"
---

# Backend Targeted Tests

Use this skill to select and run the smallest useful backend pytest set from changed files.

## When to Use

- You changed backend API logic and want quick confidence.
- You touched one feature area and want to avoid running all tests.
- You need a consistent mapping from file changes to test files.

## Inputs

- Optional base ref argument, for example `origin/main` or `HEAD~1`.
- If no argument is provided, the base ref defaults to `origin/main`.

## Procedure

1. Identify changed backend files from git diff against the base ref.
2. Map file changes to test targets:
    - Prompt flow changes (`backend/routers/prompt.py`, `backend/services/prompt_service.py`) -> `backend/tests/test_prompt_routes.py`
    - User/auth flow changes (`backend/routers/user.py`, `backend/services/user_service.py`, `backend/auth/**`) -> `backend/tests/test_user_routes.py`
    - Schema/data layer changes (`backend/db/models.py`, `backend/db/database.py`, `backend/migrations/**`) -> both route test files
    - Core app wiring changes (`backend/main.py`, `backend/core/**`) -> run full backend suite
3. Execute selected tests with `uv run pytest ...`.
4. If mapping is ambiguous or no backend files changed, fall back to both route test files.
5. If selected tests fail and the failure touches shared infrastructure, run full backend tests.

## Command

Run the helper script:

```bash
./.github/skills/backend-tests/scripts/run-targeted-tests.sh <optional-base-ref>
```

Preview selection without running tests:

```bash
./.github/skills/backend-tests/scripts/run-targeted-tests.sh --dry-run <optional-base-ref>
```

## Completion Criteria

- Selected tests pass with zero failures.
- Selection is explainable from changed files.
- Full suite is used when core/shared areas changed.

## References

- [Runner script](./scripts/run-targeted-tests.sh)
- [Backend tests](../../../backend/tests)
- [Agent guidance](../../../AGENTS.md)
