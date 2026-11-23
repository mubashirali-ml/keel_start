# ADR-0002: Multi-agent delivery process (Supervisor, Builders, Reviewer)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator |
| **Tickets** | — |
| **Scope** | `.claude/agents/`, `tickets/`, `prs/`, `scripts/`, git branching |

## Context

The product (see [product-brief.md](../product-brief.md)) is built from scratch by AI
agents. We want parallel throughput (five or more builders at once) without the usual
failure modes of parallel agents: overlapping edits, a planner that starts coding instead
of planning, unbounded review ping-pong, and "it works on my branch" merges.

## Decision

### Roles

| Role | Does | Never does | Definition |
|---|---|---|---|
| **Supervisor** | Writes architecture ADRs, splits the brief into tickets with acceptance criteria and file ownership, orders them into waves, assigns them, answers `BLOCKED` builders with decisions. | Writes or edits code, tests or scripts. It may only commit under `docs/` and `tickets/`. | [.claude/agents/supervisor.md](../../.claude/agents/supervisor.md) |
| **Builder** (×5+) | Implements exactly one ticket in its own worktree and branch, with tests and a recorded feature run; opens the PR record. | Touches files owned by another ticket; changes an accepted ADR; adds a dependency on its own. | [.claude/agents/builder.md](../../.claude/agents/builder.md) |
| **Reviewer** | Reviews a PR against the ticket and the ADRs; returns `APPROVED` or `CHANGES_REQUESTED` with concrete findings. | Edits code. It may only commit to the PR record under `prs/`. | [.claude/agents/reviewer.md](../../.claude/agents/reviewer.md) |
| **Gate** (script) | Runs [scripts/merge_pr.sh](../../scripts/merge_pr.sh): tests, fresh recording, role-scope and review checks, then the merge. | Uses judgment. It is deterministic. | ADR-0003 |

Each role commits under its own git author (`Supervisor <supervisor@agents.local>`,
`Builder T-NNN <builder-t-nnn@agents.local>`, `Reviewer <reviewer@agents.local>`), so
`git log` is an audit trail and the gate can mechanically check that the Supervisor and
Reviewer never touched code.

### One ticket = one branch = one PR

- Ticket `T-NNN` lives in `tickets/T-NNN-*.md` and lists the files and directories it
  **owns**. Tickets in the same wave own disjoint paths, so parallel builders can't collide.
- `scripts/start_ticket.sh T-NNN` creates branch `ticket/T-NNN` in an isolated worktree
  at `.worktrees/T-NNN`. A builder works only there.
- The PR is the branch plus its record `prs/T-NNN.md` (description, test evidence,
  recording, review rounds). Merging uses `--no-ff`, so every ticket is exactly one merge
  commit on `main`: `Merge PR T-NNN: <title>`.

### Waves

The Supervisor orders tickets into waves. Wave 0 is the foundation (project skeleton and
shared contracts: types, interfaces, constants), built by one builder. Each later wave
holds tickets that depend only on earlier waves and run fully in parallel.

### Review-fix loop: at most 3 rounds

```
build ─> review r1 ─APPROVED──────────────────────────────> gate ─> merge
             └─CHANGES_REQUESTED─> fix ─> review r2 ─APPROVED─> gate
                                              └─CHANGES─> fix ─> review r3 ─APPROVED─> gate
                                                                     └─CHANGES─> ESCALATED to Supervisor (not merged)
```

The Reviewer must put every blocking issue in the earliest round it can see it, and later
rounds may only raise issues in code changed by the fix. That's what makes three rounds
enough. A ticket still failing after round 3 is escalated: the Supervisor re-scopes or
splits it. It is never force-merged.

### Unblocking

A builder that hits a question outside its ticket (an unclear contract, an ADR conflict,
a missing dependency) stops and reports `BLOCKED` with the question. The Supervisor
answers with a decision (and an ADR if it affects other tickets), and a builder resumes
in the same worktree. The Supervisor answers in words; it doesn't write the fix.

### Shared environment

One `.venv` at the repository root, pre-installed from `requirements.txt`. Worktrees use
it through the scripts. Adding a package is a Supervisor decision recorded in an ADR.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Supervisor + parallel builders in worktrees + bounded review (chosen) | Parallel; isolated; auditable; bounded cost | Needs up-front contracts (wave 0) |
| B. One agent builds everything sequentially | Simple, no conflicts | Slow; no independent review; one context must hold the whole codebase |
| C. Parallel builders on one shared branch | No merge step | Agents overwrite each other; no per-ticket review or rollback |
| D. Unbounded review loop | Higher polish in theory | Can ping-pong forever; cost unpredictable |

## Consequences

- The Supervisor must define contracts before builders start; vague contracts show up
  as `BLOCKED` reports, which is the intended signal.
- File ownership makes merges mostly trivial; a conflict means a ticket boundary was wrong.
- The 3-round cap keeps cost predictable and pushes reviewers to be thorough in round 1.
- This harness is tool-agnostic: the roles are Markdown files and the gates are shell
  scripts, so any agent runner (Claude Code, a workflow engine, a human) can drive them.
