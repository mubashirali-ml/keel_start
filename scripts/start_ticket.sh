#!/usr/bin/env bash
# Create (or reuse) the isolated worktree + branch for one ticket. Prints the worktree path.
# Usage: bash scripts/start_ticket.sh T-003
. "$(dirname "$0")/lib.sh"
T="${1:-}"; check_ticket_id "$T"
ticket_file "$T" >/dev/null
WT="$(worktree_path "$T")"
BRANCH="ticket/$T"

cd "$REPO_ROOT"
if [ -d "$WT" ]; then
  echo "$WT"; exit 0
fi
mkdir -p "$WORKTREES_DIR"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git worktree add -q "$WT" "$BRANCH"
else
  git worktree add -q -b "$BRANCH" "$WT" main
fi
echo "$WT"
