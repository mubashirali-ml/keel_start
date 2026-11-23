# ADR-0004: Supervisor modes: human-in-the-loop and autonomous

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator, product owner |
| **Tickets** | — |
| **Scope** | `harness/harness.env`, `scripts/harness_args.sh`, `harness/delivery.workflow.js`, Supervisor role |

## Context

ADR-0002 defines a Supervisor that plans and unblocks on its own. The product owner also
wants to talk to the Supervisor: review the plan before builders spend effort, and answer
product questions ("should the QA agent block a deploy?") rather than have an agent guess.
But a fully autonomous run is still useful for well-understood waves. The choice must be a
setting, not a code change.

## Decision

We will support two modes, chosen by `SUPERVISOR_MODE` in `harness/harness.env`
(an environment variable of the same name overrides the file):

| | `human` | `auto` |
|---|---|---|
| Plan | Supervisor plans, commits, lists the product choices it defaulted as `open_questions`, then the run **stops**. | Supervisor plans and the run continues straight into delivery. |
| Plan changes | The product owner gives feedback; stage `revise` has the Supervisor revise ADRs/tickets (superseding, never editing, accepted ADRs). Repeat until approved. | — |
| Start building | Only when the product owner runs stage `deliver`. | Immediately after planning. |
| Builder `BLOCKED` | Technical questions: Supervisor decides. **Product** questions: ticket stops as `needs_human` with the Supervisor's recommended answer; the product owner's answer is passed in on the next `deliver` run. | Supervisor decides everything. |

Everything else (worktrees, review rounds, merge gate) is identical in both modes.
The stages are driven by `harness/delivery.workflow.js`, with arguments produced by
`bash scripts/harness_args.sh plan|revise|deliver ["feedback"]`.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Two modes behind one setting (chosen) | Same harness for supervised and unattended runs | Two paths to keep working |
| B. Always human | Maximum control | Slow; blocks unattended runs |
| C. Always auto | Fast | Agents guess product intent; costly rework when they guess wrong |

## Consequences

- In `human` mode, every product decision is either confirmed by the product owner or
  visible as an `open_question`, and plan revisions are separate Supervisor commits, so
  the history shows how the plan changed and why.
- A `needs_human` ticket keeps its worktree, so its builder resumes where it stopped.
