#!/usr/bin/env bash
# Print the JSON `args` for harness/delivery.workflow.js from harness/harness.env
# (environment variables override the file).
# Usage: bash scripts/harness_args.sh plan|ask|revise|deliver ["question or feedback text"]
. "$(dirname "$0")/lib.sh"
STAGE="${1:-plan}"; FEEDBACK="${2:-}"
case "$STAGE" in plan|ask|revise|deliver) ;; *) die "stage must be plan, ask, revise or deliver" ;; esac

val() {  # env var wins, else harness.env, else default
  local name="$1" def="$2" v
  v="${!name:-}"
  [ -n "$v" ] || v="$(grep -E "^$name=" "$REPO_ROOT/harness/harness.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r' || true)"
  echo "${v:-$def}"
}
MODE="$(val SUPERVISOR_MODE human)"
case "$MODE" in human|auto) ;; *) die "SUPERVISOR_MODE must be human or auto (got '$MODE')" ;; esac
WAVES="$(val WAVES 0,1)"
MINP="$(val MIN_PARALLEL_BUILDERS 5)"

"$VENV_PY" - "$REPO_ROOT" "$MODE" "$STAGE" "$WAVES" "$MINP" "$FEEDBACK" <<'PY'
import json, sys
repo, mode, stage, waves, minp, feedback = sys.argv[1:7]
print(json.dumps({
    "repo": repo.replace("\\", "/"),
    "mode": mode,
    "stage": stage,
    "waves": [int(w) for w in waves.split(",") if w.strip()],
    "minParallel": int(minp),
    "feedback": feedback,
    "question_answers": {},
    "answers": {},
}))
PY
