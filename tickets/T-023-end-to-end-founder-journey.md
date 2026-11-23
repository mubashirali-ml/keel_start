# T-023: End-to-end founder journey: API test suite and recorded browser demo

| | |
|---|---|
| **Wave** | 5 |
| **Depends on** | T-018, T-019, T-020, T-021, T-022 |
| **ADRs** | [ADR-0003](../docs/adr/0003-merge-gate-tests-and-recorded-run.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md) |
| **Status** | todo |

## Goal

Prove the product's definition of done: a founder goes from the first chat message to a
verified name and domain choice, executed founding documents, a cap table, a QA-passed
live (or packaged) website and a registration checklist, through the API and the UI,
with LLM, RDAP and hosting faked; and give the owner a short guide to run it.

## Owns (only these paths may change)

- `tests/test_e2e_journey.py`
- `docs/running-the-app.md`
- `evidence/T-023/`
- `prs/T-023.md`

## Contracts

- **Provides:** the journey test and the recorded demo; a plain-language run guide (how to start the app, which environment variables turn on DeepSeek/Groq, live RDAP and Netlify, and the first-release limitations: no real sign-in or e-signature, not legal advice, the app does not file or buy anything).
- **Consumes:** the whole product (T-001–T-022), `running_app`/`capture_matrix` (T-011), API (T-016, T-017).

## Acceptance criteria

1. `tests/test_e2e_journey.py` drives the full journey through `TestClient` from `POST /api/cases` using only chat messages and the HTTP actions a founder would use, and asserts: facts locked with the default-vesting note; Law, Name, Website and Guide handovers and returns in the chat with correct agent labels; a chosen name with a domain whose status is `available`; documents generated, an edit that invalidated a signature, a rejected stale signature, then every document executed and `legal_complete`; the cap table totalling 10,000,000 with matching document share counts; a website build that needed one QA fix round and was deployed to the fake host; a second case with hosting not configured ending as "packaged"; every checklist item ticked and progress at 100%.
2. The same journey covers one failure path per step (equity not 100, a taken `.com`, a stale signature, a QA failure needing explicit override, a guide request before the state is known) and asserts friendly messages.
3. The recorded run drives the same journey in the browser and saves the screenshot matrix for every view (chat, overview, names, legal, audit, cap table, website, guide) at the end state.
4. If the journey reveals a defect in another ticket's code, the builder reports `BLOCKED` with the failing assertion instead of editing that code.

## Feature run (`evidence/T-023/feature_run.py`)

Builds the frontend, starts `running_app(seed_stage="new")`, and as a founder in the
browser (switching between Alice and Bob in the header for approvals): chats through the
whole journey (business, founders, entity and state, legal question, names and choice,
confirmation, documents with an edit and approvals by both founders, cap table download,
website request with a Pricing page and testimonials, QA fix round, deploy, registration
checklist ticks), printing each step and asserting what is visible. Saves the screenshot
matrices of every view and prints a final summary table of the definition-of-done items
with PASS for each.

## Out of scope

New features or fixes in other tickets' files.
