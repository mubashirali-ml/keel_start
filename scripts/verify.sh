#!/usr/bin/env bash
# Pre-review / pre-merge verification for one ticket (ADR-0003). Run inside the ticket worktree.
# Checks: branch, file ownership, role scope, pytest, recorded feature run, PR record.
# Usage: bash scripts/verify.sh T-003
. "$(dirname "$0")/lib.sh"
T="${1:-}"; check_ticket_id "$T"
TOPLEVEL="$(git rev-parse --show-toplevel)"
cd "$TOPLEVEL"
FAIL=0
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAIL=1; }

# 1. Right branch
BR="$(git rev-parse --abbrev-ref HEAD)"
[ "$BR" = "ticket/$T" ] && pass "on branch $BR" || fail "expected branch ticket/$T, on '$BR' (run inside .worktrees/$T)"

# 2. File ownership: every path changed by this branch (committed or not) must be owned.
mapfile -t OWNED < <(ticket_owned_paths "$T")
[ "${#OWNED[@]}" -gt 0 ] || fail "ticket has no backticked paths under '## Owns'"
CHANGED="$( { git diff --name-only main...HEAD; git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u )"
NEW_ADRS="$(git diff --name-only --diff-filter=A main...HEAD -- docs/adr/ ; git ls-files --others --exclude-standard -- docs/adr/)"
BAD=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  ok=0
  case "$f" in "evidence/$T/"*|"prs/$T.md") ok=1 ;; esac
  if [ $ok = 0 ] && grep -qxF "$f" <<<"$NEW_ADRS" && [[ "$f" =~ ^docs/adr/[0-9]{4}-.*\.md$ ]]; then ok=1; fi
  for p in "${OWNED[@]}"; do
    case "$p" in */) [[ "$f" == "$p"* ]] && ok=1 ;; *) [ "$f" = "$p" ] && ok=1 ;; esac
  done
  [ $ok = 1 ] || BAD+="$f "
done <<<"$CHANGED"
[ -z "$BAD" ] && pass "all changed files are owned by $T" || fail "files outside $T's ownership: $BAD"

# 3. Role scope over the whole history: Supervisor only docs/ + tickets/, Reviewer only prs/ + ADR status.
SUP="$(git log --all --author='supervisor@agents.local' --name-only --format= | sort -u | grep -vE '^(docs/|tickets/|$)' || true)"
[ -z "$SUP" ] && pass "Supervisor commits touch only docs/ and tickets/" || fail "Supervisor touched code: $SUP"
REV="$(git log --all --author='reviewer@agents.local' --name-only --format= | sort -u | grep -vE '^(prs/|docs/adr/[0-9]{4}-|$)' || true)"
[ -z "$REV" ] && pass "Reviewer commits touch only prs/ (and ADR status)" || fail "Reviewer touched code: $REV"

# 4. Tests
if bash "$REPO_ROOT/scripts/py.sh" -m pytest -q -p no:cacheprovider >"$TOPLEVEL/.verify-pytest.log" 2>&1; then
  pass "pytest: $(tail -1 "$TOPLEVEL/.verify-pytest.log")"
else
  fail "pytest failed:"; tail -40 "$TOPLEVEL/.verify-pytest.log"
fi
rm -f "$TOPLEVEL/.verify-pytest.log"

# 4b. Frontend (ADR-0005): if this checkout has a frontend, it must install, build and pass its tests.
if [ -f frontend/package.json ]; then
  # (Re)install when node_modules is missing or older than the lockfile (e.g. main added a package).
  if [ ! -d frontend/node_modules ] || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
    if [ -f frontend/package-lock.json ]; then (cd frontend && npm ci --no-audit --no-fund --loglevel=error) >/dev/null 2>&1
    else (cd frontend && npm install --no-audit --no-fund --loglevel=error) >/dev/null 2>&1; fi \
      || fail "frontend: npm install failed"
  fi
  if (cd frontend && npm run -s build) >"$TOPLEVEL/.verify-fe.log" 2>&1; then pass "frontend: build"
  else fail "frontend: build failed:"; tail -30 "$TOPLEVEL/.verify-fe.log"; fi
  if grep -q '"test"[[:space:]]*:' frontend/package.json; then
    if (cd frontend && npm test --silent) >"$TOPLEVEL/.verify-fe.log" 2>&1; then pass "frontend: tests"
    else fail "frontend: tests failed:"; tail -30 "$TOPLEVEL/.verify-fe.log"; fi
  else
    fail "frontend: package.json has no \"test\" script (ADR-0005)"
  fi
  rm -f "$TOPLEVEL/.verify-fe.log"
fi

# 5. Recorded feature run
if bash "$REPO_ROOT/scripts/record_run.sh" "$T" >/dev/null 2>&1; then
  pass "recorded feature run exits 0 (evidence/$T/run.log)"
else
  fail "feature run failed or missing; see evidence/$T/run.log"; tail -30 "evidence/$T/run.log" 2>/dev/null || true
fi

# 6. PR record
[ -f "prs/$T.md" ] && pass "PR record prs/$T.md exists" || fail "missing PR record prs/$T.md"

echo
if [ $FAIL = 0 ]; then echo "VERIFY $T: PASS"; else echo "VERIFY $T: FAIL"; exit 1; fi
