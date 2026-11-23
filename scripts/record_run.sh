#!/usr/bin/env bash
# Run a ticket's feature run and record it to evidence/T-NNN/run.log (ADR-0003).
# Run from inside the ticket's worktree. Exit code = the feature run's exit code.
# Usage: bash scripts/record_run.sh T-003
. "$(dirname "$0")/lib.sh"
T="${1:-}"; check_ticket_id "$T"
TOPLEVEL="$(git rev-parse --show-toplevel)"
cd "$TOPLEVEL"
SCRIPT="evidence/$T/feature_run.py"
LOG="evidence/$T/run.log"
[ -f "$SCRIPT" ] || die "$SCRIPT not found (every ticket ships a feature run)"

DIRTY="$(git status --porcelain -- . ":(exclude)evidence/" ":(exclude)prs/" | wc -l | tr -d ' ')"
TMP="$(mktemp)"
set +e
bash "$REPO_ROOT/scripts/py.sh" "$SCRIPT" >"$TMP" 2>&1
CODE=$?
set -e

{
  echo "# Recorded feature run"
  echo "ticket:      $T"
  echo "branch:      $(git rev-parse --abbrev-ref HEAD)"
  echo "commit:      $(git rev-parse HEAD)"
  echo "uncommitted: $DIRTY file(s) outside evidence/ and prs/"
  echo "recorded_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "python:      $("$VENV_PY" -c 'import sys; print(sys.version.split()[0])')"
  echo "command:     bash scripts/py.sh $SCRIPT"
  echo "exit_code:   $CODE"
  echo "----------------------------------------------------------------------"
  tr -d '\r' <"$TMP"
} >"$LOG"
rm -f "$TMP"
echo "recorded $LOG (exit $CODE)"
exit "$CODE"
