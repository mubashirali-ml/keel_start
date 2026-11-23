#!/usr/bin/env bash
# The merge gate (ADR-0003). The only way code reaches main.
# Exit codes: 0 merged, 1 gate failed, 2 merge conflict with main (builder must resolve).
# Usage: bash scripts/merge_pr.sh T-003
. "$(dirname "$0")/lib.sh"
T="${1:-}"; check_ticket_id "$T"
WT="$(worktree_path "$T")"
BRANCH="ticket/$T"
TITLE="$(ticket_title "$T")"

cd "$REPO_ROOT"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "main checkout is not on main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "main checkout has uncommitted changes"
[ -d "$WT" ] || die "no worktree for $T at $WT"

cd "$WT"
[ -z "$(git status --porcelain)" ] || die "$T worktree has uncommitted changes; commit them first"

# 1. Bring the branch up to date with main, so every check runs on the post-merge code.
if ! "${GATE_GIT[@]}" merge --no-edit -q main -m "gate: merge main into $BRANCH" >/dev/null 2>&1; then
  echo "CONFLICT: $BRANCH does not merge cleanly with main. Conflicting files:"
  git diff --name-only --diff-filter=U || true
  git merge --abort || true
  exit 2
fi

# 2-3, 5. Tests, fresh recording on the merged code, ownership and role scope.
bash "$REPO_ROOT/scripts/verify.sh" "$T" || { echo "GATE $T: FAIL (verify)"; exit 1; }
if [ -n "$(git status --porcelain -- "evidence/$T")" ]; then
  git add "evidence/$T"
  "${GATE_GIT[@]}" commit -q -m "gate: $T re-record feature run on merged code" -m "$TRAILER"
fi

# 4. Review: last verdict APPROVED, at most 3 rounds.
PR="prs/$T.md"
ROUNDS="$(grep -cE '^### Round [0-9]+' "$PR" || true)"
LAST="$(grep -E '^Verdict:' "$PR" | tail -1 | sed -E 's/^Verdict:[[:space:]]*//; s/[[:space:]]*$//')"
[ "$ROUNDS" -ge 1 ] || { echo "GATE $T: FAIL (no review rounds in $PR)"; exit 1; }
[ "$ROUNDS" -le 3 ] || { echo "GATE $T: FAIL ($ROUNDS review rounds > 3; escalate to Supervisor)"; exit 1; }
[ "$LAST" = "APPROVED" ] || { echo "GATE $T: FAIL (last verdict is '$LAST', not APPROVED)"; exit 1; }
echo "PASS  review: $ROUNDS round(s), last verdict APPROVED"

# 6. ADRs added by this branch must be Accepted.
for adr in $(git diff --name-only --diff-filter=A main...HEAD -- docs/adr/); do
  grep -qE '^\|[[:space:]]*\*\*Status\*\*[[:space:]]*\|[[:space:]]*Accepted' "$adr" \
    || { echo "GATE $T: FAIL ($adr is not Accepted)"; exit 1; }
done
echo "PASS  every ADR added by $T is Accepted"

# Merge: one ticket = one merge commit on main.
cd "$REPO_ROOT"
"${GATE_GIT[@]}" merge --no-ff -q "$BRANCH" -m "Merge PR $T: $TITLE" \
  -m "Gate: tests passed, feature run recorded (evidence/$T/run.log), review approved in $ROUNDS round(s)." \
  -m "$TRAILER"
git worktree remove "$WT"
echo "GATE $T: MERGED into main as $(git rev-parse --short HEAD)"
