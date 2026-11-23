# Startup Launch Agents (agent-built)

A founder chats with a **Manager Agent**, which brings in specialists: a **Law Agent**
(legal questions and founding documents), a **Name Agent** (names plus live domain
checks), a **Website Agent** that builds and deploys the company site, a **QA Agent** that
checks the site against what the founder asked for, and a **Registration Guide Agent**
(state filing steps and buying the domain). It also builds the cap table, tracks the IRS
83(b) deadline, and runs multi-founder sign-off on the documents.
Full requirements: [docs/product-brief.md](docs/product-brief.md).

This repository is built **from scratch by a team of AI agents** under a fixed,
auditable process. The process is as much a deliverable as the app.

There are two groups of agents here, and they are different things:

| | Who talks to them | What they do |
|---|---|---|
| **Delivery agents** (Supervisor, Builders, Reviewer) | The developer / product owner | Build this codebase: ADRs, tickets, code, tests, reviews |
| **Product agents** (Manager, Law, Name, Website, QA, Registration Guide) | The app's end users (founders) | Run inside the finished app |

## The delivery process

```
                 docs/product-brief.md
                          │
                    ┌─────▼──────┐   writes ADRs + tickets (docs/, tickets/ only)
                    │ Supervisor │◄──────────── BLOCKED? ──────────────┐
                    └─────┬──────┘   answers with a decision          │
          assigns one ticket per builder, wave by wave                │
   ┌──────────┬──────────┼──────────┬──────────┐                     │
┌──▼───┐  ┌───▼──┐  ┌────▼─┐  ┌─────▼┐  ┌──────▼┐   each in its own    │
│B T-02│  │B T-03│  │B T-04│  │B T-05│  │B T-06 │   worktree + branch ─┘
└──┬───┘  └───┬──┘  └────┬─┘  └─────┬┘  └──────┬┘   ticket/T-NNN
   └──────────┴────┬─────┴──────────┴──────────┘
             ┌─────▼────┐  APPROVED / CHANGES_REQUESTED → builder fixes
             │ Reviewer │  at most 3 rounds, then escalate to Supervisor
             └─────┬────┘
             ┌─────▼────┐  main merged in · pytest · recorded feature run ·
             │   Gate   │  review approved · role scope · ADRs accepted
             └─────┬────┘
                main  (one --no-ff merge commit per ticket: "Merge PR T-NNN: …")
```

| Requirement | Where it lives |
|---|---|
| Supervisor plans, assigns, unblocks; never writes code | [.claude/agents/supervisor.md](.claude/agents/supervisor.md); the gate fails if any Supervisor commit touches a path outside `docs/` and `tickets/` |
| 5+ parallel builders, one ticket = one PR, isolated branches | [.claude/agents/builder.md](.claude/agents/builder.md), [scripts/start_ticket.sh](scripts/start_ticket.sh) (worktree `.worktrees/T-NNN`, branch `ticket/T-NNN`), PR records in [prs/](prs/), file ownership per ticket |
| Reviewer with a review-fix loop of at most 3 rounds | [.claude/agents/reviewer.md](.claude/agents/reviewer.md); the gate counts `### Round N` in the PR record |
| Tests + recorded feature run before merging | [scripts/verify.sh](scripts/verify.sh), [scripts/record_run.sh](scripts/record_run.sh), [scripts/merge_pr.sh](scripts/merge_pr.sh); logs in [evidence/](evidence/) |
| ADRs throughout | [docs/adr/](docs/adr/): process ADRs 0001–0004, architecture ADRs by the Supervisor, `Proposed` ADRs by builders accepted at review |

Every role commits under its own git identity, so `git log --format='%an %s'` shows who
did what, and `git log --merges --first-parent main` lists one merge per ticket.

## Running the harness

The roles are plain Markdown and the gates are Bash scripts, so any agent runner can
drive them. This repo is driven with Claude Code using
[harness/delivery.workflow.js](harness/delivery.workflow.js) (Supervisor → parallel
Builders → Reviewer loop → Gate).

### Talking to the Supervisor: `SUPERVISOR_MODE` (ADR-0004)

Set it in [harness/harness.env](harness/harness.env), or override it per run with an
environment variable.

- `human`: the Supervisor plans, then **stops for your approval**. You read the ADRs and
  tickets, send feedback (stage `revise`) as often as you like, then start building
  (stage `deliver`). Builder questions about what the product should do come to you.
- `auto`: plan and build run straight through, and the Supervisor decides everything.

```bash
bash scripts/harness_args.sh plan                         # args for the planning run
bash scripts/harness_args.sh revise "split T-004 in two"  # args for a plan revision
bash scripts/harness_args.sh deliver                      # args for building the waves in WAVES
SUPERVISOR_MODE=auto bash scripts/harness_args.sh plan    # one-off autonomous run
```

In Claude Code, ask: *"run harness/delivery.workflow.js with the args from
`bash scripts/harness_args.sh plan`"*.

### Scripts each role uses

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # once
bash scripts/start_ticket.sh T-002     # builder: create worktree + branch
bash scripts/verify.sh T-002           # builder/reviewer: ownership, scope, tests, recording
bash scripts/merge_pr.sh T-002         # gate: the only path to main
```

## Status

See [tickets/BACKLOG.md](tickets/BACKLOG.md) for the plan and progress.
