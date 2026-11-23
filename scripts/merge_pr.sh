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
# A leftover re-recording of this ticket's run.log (e.g. from the Reviewer running verify.sh) is not work:
# the gate records a fresh one on the merged code anyway, so restore it. Anything else must be committed.
if [ "$(git status --porcelain)" = " M evidence/$T/run.log" ]; then
  git checkout -q -- "evidence/$T/run.log"
  echo "note: restored an uncommitted re-recording of evidence/$T/run.log (the gate records a fresh one)"
fi
[ -z "$(git status --porcelain)" ] || die "$T worktree has uncommitted changes; commit them first"

# 4. Review: last verdict APPROVED, at most 3 rounds. (Checked first: a refused PR leaves no gate commits.)
PR="prs/$T.md"
[ -f "$PR" ] || { echo "GATE $T: FAIL (missing $PR)"; exit 1; }
# Only the Reviewer's section counts: rounds and verdicts under "## Review" (up to the next "## " heading).
# Builder replies elsewhere in the record (e.g. "## Builder response" / "### Round 1") are ignored.
REVIEW="$(awk '/^## Review[[:space:]]*$/{on=1; next} /^## /{on=0} on' "$PR")"
ROUNDS="$(grep -cE '^### Round [0-9]+' <<<"$REVIEW" || true)"
LAST="$(grep -E '^Verdict:' <<<"$REVIEW" | tail -1 | sed -E 's/^Verdict:[[:space:]]*//; s/[[:space:]]*$//')"
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

# 1. Bring the branch up to date with main, so every check runs on the post-merge code.
PRE_GATE="$(git rev-parse HEAD)"
if ! "${GATE_GIT[@]}" merge --no-edit -q main -m "gate: merge main into $BRANCH" >/dev/null 2>&1; then
  echo "CONFLICT: $BRANCH does not merge cleanly with main. Conflicting files:"
  git diff --name-only --diff-filter=U || true
  git merge --abort || true
  exit 2
fi

# 2-3, 5. Tests, fresh recording on the merged code, ownership and role scope.
if ! bash "$REPO_ROOT/scripts/verify.sh" "$T"; then
  # Leave the branch as the builder had it: undo the gate's main-merge and the re-recording.
  git reset -q --hard "$PRE_GATE"
  git clean -fq -- "evidence/$T/run.log"
  echo "GATE $T: FAIL (verify on code merged with main; branch reset to pre-gate state)"; exit 1
fi
if [ -n "$(git status --porcelain -- "evidence/$T")" ]; then
  git add "evidence/$T"
  "${GATE_GIT[@]}" commit -q -m "gate: $T re-record feature run on merged code" -m "$TRAILER"
fi

# Merge: one ticket = one merge commit on main.
cd "$REPO_ROOT"
"${GATE_GIT[@]}" merge --no-ff -q "$BRANCH" -m "Merge PR $T: $TITLE" \
  -m "Gate: tests passed, feature run recorded (evidence/$T/run.log), review approved in $ROUNDS round(s)." \
  -m "$TRAILER"
git worktree remove "$WT"
echo "GATE $T: MERGED into main as $(git rev-parse --short HEAD)"
