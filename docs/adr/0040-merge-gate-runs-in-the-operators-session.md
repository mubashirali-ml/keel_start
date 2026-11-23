# ADR-0040: The merge gate runs in the operator's session

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator |
| **Tickets** | T-001 (where the problem surfaced) |
| **Scope** | `harness/delivery.workflow.js`, `scripts/merge_pr.sh`; amends how ADR-0002/0003's gate is triggered |

## Context

In the first delivery run, T-001 was approved by the Reviewer in round 3 but did not merge:

1. The workflow asked a background subagent to run `bash scripts/merge_pr.sh T-001`. Claude Code's
   auto-mode safety check refused, because it flags a merge into `main` by an unattended agent as
   risky. That was a reasonable call, since nobody was there to approve it.
2. The workflow treated "the gate didn't run" as "the code failed the gate", sent the ticket back
   to the builder, and cleared the approval. That used up the three review rounds, and the ticket
   was escalated even though nothing was wrong with it.
3. Separately, `merge_pr.sh` counted every `### Round N` heading in the PR record, including the
   builder's replies under "Builder response", so it would have counted 5 rounds instead of 3.

## Decision

- **The gate is triggered by the operator in the interactive session.** By default
  (`gate: 'operator'`), the delivery workflow ends a ticket at Reviewer approval with outcome
  `approved`. The operator then runs `bash scripts/merge_pr.sh T-NNN` for each approved ticket. The
  script is unchanged as the only path to `main`, and all of its checks still apply.
- A wave stops after its tickets are approved. The next wave starts in a new delivery run, once its
  dependencies have merged.
- If an agent is configured to run the gate (`gate: 'agent'`) and the gate cannot run, the ticket is
  reported as `approved`. It is never sent back for fixes, and no review rounds are used.
- `merge_pr.sh` counts rounds and verdicts only inside the PR record's `## Review` section.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Operator runs the gate after each wave (chosen) | Merges into `main` happen where a person can see and approve them; works with safety checks on | One manual step per wave |
| B. Pre-approve `merge_pr.sh` for agents in permission settings | Fully automatic | Loosens a safety boundary for an action that changes `main`; settings are the user's call |
| C. Keep the agent gate and retry | No change | Fails the same way, and wastes review rounds |

## Consequences

- Each wave is one delivery run plus one gate step. The gate's output is visible in the session.
- T-001 merged through the gate with 590 tests passing (merge commit 7ad2082).
