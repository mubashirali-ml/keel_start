# Startup Incorporation & Compliance Engine (agent-built)

Founders describe their startup in a chat. The app checks the terms, drafts the legal
documents, builds the cap table, and gets every founder to sign off.
Full requirements: [docs/product-brief.md](docs/product-brief.md).

This repository is built **from scratch by a team of AI agents** under a fixed,
auditable process. The process is as much a deliverable as the app.

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
| ADRs throughout | [docs/adr/](docs/adr/): process ADRs 0001–0003, architecture ADRs by the Supervisor, `Proposed` ADRs by builders accepted at review |

Every role commits under its own git identity, so `git log --format='%an %s'` shows who
did what, and `git log --merges --first-parent main` lists one merge per ticket.

## Running the harness

The roles are plain Markdown and the gates are Bash scripts, so any agent runner can
drive them. This repo was driven with Claude Code (a workflow script that runs
Supervisor → parallel Builders → Reviewer loop → Gate).

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # once
bash scripts/start_ticket.sh T-002     # builder: create worktree + branch
bash scripts/verify.sh T-002           # builder/reviewer: ownership, scope, tests, recording
bash scripts/merge_pr.sh T-002         # gate: the only path to main
```

## Status

See [tickets/BACKLOG.md](tickets/BACKLOG.md) for the plan and progress.
