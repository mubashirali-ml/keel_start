# ADR-0006: Product owner ↔ Supervisor interaction

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Harness operator, product owner |
| **Tickets** | — |
| **Scope** | Supervisor role, `tickets/plan.json`, `docs/product-decisions.md`, `scripts/supervisor_desk.py`, `harness/delivery.workflow.js` stages |

## Context

ADR-0004 lets the product owner steer the Supervisor in `human` mode. The owner requires
that this is a **good experience**: they shouldn't have to read raw ticket Markdown, decode
jargon, or write long instructions to make a simple choice. They also need to see where
the build stands at a glance.

## Decision

1. **The Supervisor talks like a product lead, not a compiler.** Every run returns an
   `owner_brief`: a few short paragraphs in plain language covering what it decided,
   what the owner will be able to see or use after each wave, and what it needs from
   them. No file paths or jargon in the brief.
2. **Questions come with answers.** Every open question is structured as
   `{id, question, why_it_matters, options[2-4]{label, description}, recommended}`, so
   the owner can answer in one click (or type their own). Builder questions that need
   the owner (`needs_human`) use the same shape.
3. **One machine-readable plan.** The Supervisor maintains `tickets/plan.json` (owner
   brief, waves with a plain-language goal, tickets with a one-line `summary_for_owner`,
   ADR list, open questions with status and answers) next to the human-readable
   `tickets/BACKLOG.md`. Tools read the JSON; people read the Markdown.
4. **Supervisor Desk.** `bash scripts/py.sh scripts/supervisor_desk.py` renders
   `harness/desk.html` (git-ignored, self-contained, light/dark): the owner brief, open
   questions with the recommended answer, waves and tickets with live status taken from
   git (branch, review rounds and verdict, gate result, recorded-run exit code,
   screenshots), and recent activity by role. It's regenerated after every run.
5. **Conversation stages** (`harness/delivery.workflow.js`, args from
   `scripts/harness_args.sh`):
   - `plan`: first plan; stops for the owner in `human` mode.
   - `ask "<question>"`: the owner asks anything ("why is the Law Agent two tickets?").
     The Supervisor answers read-only: no commits.
   - `revise "<feedback>"`: answers to open questions and/or free-form changes. The
     Supervisor updates ADRs (superseding accepted ones), tickets and `plan.json`.
   - `deliver`: build the configured waves.
6. **Every owner decision is logged** by the Supervisor in `docs/product-decisions.md`
   (date, question, answer, what it changed, with ADR/ticket links), so the reasons for
   product choices outlive the chat.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Structured questions + plain-language brief + generated desk + decision log (chosen) | Fast one-click decisions; clear status at a glance; decisions durable in git | Supervisor must keep `plan.json` in sync |
| B. Owner reads tickets/ADRs directly and writes feedback | No extra tooling | Slow; jargon-heavy; easy to miss what needs a decision |
| C. A full web app for the Supervisor | Richest UX | A second product to build and maintain before the real one |

## Consequences

- The owner can steer with a few clicks and short sentences, and can always see why
  something was decided (`docs/product-decisions.md`, ADRs).
- `tickets/plan.json` becomes a contract between the Supervisor and the desk and
  workflow; the plan check validates it.
