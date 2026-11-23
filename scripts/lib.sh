# Shared helpers for the harness scripts. Source it: . "$(dirname "$0")/lib.sh"
set -euo pipefail

# Root of the MAIN checkout, even when called from inside a worktree.
REPO_ROOT="$(cd "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")" && pwd)"
WORKTREES_DIR="$REPO_ROOT/.worktrees"

if [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
  VENV_PY="$REPO_ROOT/.venv/Scripts/python.exe"
else
  VENV_PY="$REPO_ROOT/.venv/bin/python"
fi

GATE_GIT=(git -c user.name="Gate" -c user.email="gate@agents.local")
TRAILER="Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

die() { echo "ERROR: $*" >&2; exit 1; }

check_ticket_id() {
  [[ "${1:-}" =~ ^T-[0-9]{3}$ ]] || die "ticket id must look like T-001 (got '${1:-}')"
}

worktree_path() { echo "$WORKTREES_DIR/$1"; }

ticket_file() {
  local f
  f="$(ls "$REPO_ROOT"/tickets/"$1"-*.md 2>/dev/null | head -1 || true)"
  [ -n "$f" ] || die "no ticket file tickets/$1-*.md on main"
  echo "$f"
}

ticket_title() {
  head -1 "$(ticket_file "$1")" | sed -E 's/^#[[:space:]]*T-[0-9]{3}:[[:space:]]*//'
}

# Paths listed as `backticked` bullets under the "## Owns" heading of the ticket.
ticket_owned_paths() {
  awk '/^## Owns/{on=1; next} /^## /{on=0} on' "$(ticket_file "$1")" \
    | grep -oE '`[^`]+`' | tr -d '`' | sed -E 's#^\./##' | grep -v '^$' || true
}
