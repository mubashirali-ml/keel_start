#!/usr/bin/env bash
# Run the shared .venv Python with the CURRENT checkout (main or a worktree) on the path.
# Usage: bash scripts/py.sh -m pytest -q
. "$(dirname "$0")/lib.sh"
TOPLEVEL="$(git rev-parse --show-toplevel)"
export PYTHONPATH="$TOPLEVEL${PYTHONPATH:+;$PYTHONPATH}"
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1
cd "$TOPLEVEL"
exec "$VENV_PY" "$@"
