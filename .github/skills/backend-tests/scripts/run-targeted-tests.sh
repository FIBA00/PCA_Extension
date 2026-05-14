#!/usr/bin/env bash
# Selects backend pytest targets from changed files and runs the minimal useful set.
set -euo pipefail

DRY_RUN=0
BASE_REF="origin/main"

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ $# -gt 0 ]]; then
  BASE_REF="$1"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../" && pwd)"

if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "This script must run inside a git repository."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not found in PATH."
  exit 1
fi

changed_files="$(git -C "$REPO_ROOT" diff --name-only "$BASE_REF"...HEAD -- backend 2>/dev/null || true)"
if [[ -z "$changed_files" ]]; then
  changed_files="$(git -C "$REPO_ROOT" diff --name-only -- backend 2>/dev/null || true)"
fi

declare -A selected
run_full=0

while IFS= read -r file; do
  [[ -z "$file" ]] && continue

  case "$file" in
    backend/routers/prompt.py|backend/services/prompt_service.py|backend/tests/test_prompt_routes.py)
      selected["tests/test_prompt_routes.py"]=1
      ;;
    backend/routers/user.py|backend/services/user_service.py|backend/auth/*|backend/tests/test_user_routes.py)
      selected["tests/test_user_routes.py"]=1
      ;;
    backend/db/models.py|backend/db/database.py|backend/migrations/*)
      selected["tests/test_prompt_routes.py"]=1
      selected["tests/test_user_routes.py"]=1
      ;;
    backend/main.py|backend/core/*)
      run_full=1
      ;;
    backend/tests/test_*.py)
      selected["tests/${file#backend/tests/}"]=1
      ;;
  esac
done <<< "$changed_files"

if [[ $run_full -eq 0 && ${#selected[@]} -eq 0 ]]; then
  selected["tests/test_prompt_routes.py"]=1
  selected["tests/test_user_routes.py"]=1
fi

echo "Base ref: $BASE_REF"
echo "Changed backend files:"
if [[ -n "$changed_files" ]]; then
  echo "$changed_files"
else
  echo "(none detected; using fallback test set)"
fi

if [[ $run_full -eq 1 ]]; then
  echo "Selected: full backend test suite"
  if [[ $DRY_RUN -eq 0 ]]; then
    cd "$REPO_ROOT/backend"
    uv run pytest
  fi
  exit 0
fi

tests=()
for test_path in "${!selected[@]}"; do
  tests+=("$test_path")
done

IFS=$'\n' tests=($(sort <<<"${tests[*]}"))
unset IFS

echo "Selected tests:"
printf '%s\n' "${tests[@]}"

if [[ $DRY_RUN -eq 0 ]]; then
  cd "$REPO_ROOT/backend"
  uv run pytest "${tests[@]}"
fi
