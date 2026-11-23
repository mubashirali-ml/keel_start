# ADR-0003: Merge gate: tests plus a recorded feature run

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator |
| **Tickets** | — |
| **Scope** | `scripts/verify.sh`, `scripts/record_run.sh`, `scripts/merge_pr.sh`, `evidence/` |

## Context

AI builders can write tests that pass while the feature doesn't actually work as a whole,
and a reviewer reading a diff can miss that too. We want proof that the feature runs, on
exactly the code being merged, and we want that proof kept in the repository.

## Decision

Nothing merges to `main` except through `scripts/merge_pr.sh T-NNN`, which refuses the
merge unless all of the following hold:

1. **Up to date.** `main` is merged into the ticket branch first, so the checks run on
   what `main` will look like after the merge. A merge conflict stops the gate and goes
   back to the builder.
2. **Tests pass.** `pytest` passes on the whole repository (not just the ticket's tests).
3. **Recorded feature run.** Each ticket ships `evidence/T-NNN/feature_run.py`: a script
   that exercises the feature end to end the way a user or caller would (real inputs, real
   outputs printed, assertions on key results). The gate runs it with
   `scripts/record_run.sh`, which writes `evidence/T-NNN/run.log` with a header (ticket,
   branch, commit, UTC time, Python version, command, exit code) and the full output.
   The run must exit 0. The gate re-records on the merged code and commits the log, so
   the recording always matches what lands on `main`.
4. **Approved review.** `prs/T-NNN.md` contains review rounds, the last one is
   `Verdict: APPROVED`, and there are at most 3 rounds.
5. **Role scope.** Commits by the Supervisor touch only `docs/` and `tickets/`; commits
   by the Reviewer touch only `prs/`. Builders never touch another ticket's evidence or
   PR record.
6. **ADR status.** Any ADR added by the branch is `Accepted` (the Reviewer flips
   `Proposed` to `Accepted` when it approves).

LLM-dependent features are recorded with the deterministic fake LLM provider, so
recordings need no paid key and are reproducible. A live-provider run is optional extra
evidence, never a gate.

UI tickets also record a run: a headless script that drives the Streamlit app (or the API
the UI calls) and saves the transcript, plus a screen recording when the ticket asks for one.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Tests + fresh recorded run, re-run at merge (chosen) | Proves the feature runs on the merged code; evidence lives in git | A few extra seconds per merge |
| B. Tests only | Simple | Unit tests can pass while integration is broken |
| C. Builder-recorded run accepted as-is | Cheaper | The recording goes stale as soon as `main` moves or a fix lands |

## Consequences

- `evidence/` grows by one small log per ticket. Logs are plain text and diffable.
- A feature run script is also living documentation of how to use the feature.
- The gate is the only path to `main`. Nobody, including the Supervisor, merges by hand.
