# Working in this repository

This repo is built by agents under a fixed process. Before doing anything, find your role:

- **Supervisor**: [.claude/agents/supervisor.md](.claude/agents/supervisor.md). Plans, writes ADRs and tickets, unblocks. Never writes code.
- **Builder**: [.claude/agents/builder.md](.claude/agents/builder.md). One ticket, one worktree, one PR.
- **Reviewer**: [.claude/agents/reviewer.md](.claude/agents/reviewer.md). At most 3 review rounds. Never edits code.

Process: [ADR-0002](docs/adr/0002-multi-agent-delivery-process.md). Merge gate: [ADR-0003](docs/adr/0003-merge-gate-tests-and-recorded-run.md).
Why ADRs: [ADR-0001](docs/adr/0001-record-architecture-decisions.md).

Rules every role follows:

- `main` changes only through `bash scripts/merge_pr.sh T-NNN`. Never commit code to `main` directly.
- Python only through `bash scripts/py.sh` (shared `.venv`, current checkout on the path).
- Commit under your role's git identity (see your role file). End every commit message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Accepted ADRs are immutable; supersede them with a new ADR.
