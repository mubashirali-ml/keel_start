# T-018: Chat experience and Overview screen

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-039, T-041 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md) |
| **Status** | todo |

## Goal

The founder chats with the Manager and specialists in a clean conversation view where
every agent has its own name, icon and color, handovers appear inline, a typing indicator
shows while an agent is answering and suggested replies are one click away; the Overview
shows progress across all steps and the 83(b) countdown.

## Owns (only these paths may change)

- `frontend/src/features/chat/`
- `frontend/src/features/overview/`
- `evidence/T-018/`
- `prs/T-018.md`

## Contracts

- **Provides:** `ChatPanel` (default export of `features/chat/index.tsx`, used by the shell) and the Overview page.
- **Consumes:** `@/design`, `@/agents`, `@/api` hooks (`useMessages`, `usePostMessage`, `useCase`), `useMe`, `useJob`, `PlanGate` (T-011); endpoints from T-041.

## Acceptance criteria

1. Messages render per role: founder bubbles (right, with the sending founder's name; "You" for the logged-in user), agent messages (left) with `AgentAvatar`, display name and accent; `handoff` messages render as a centered inline banner ("Manager brought in the Law Agent" / "… handed the conversation back to the Manager"); `validation` messages list issues clearly; `name_options`, `documents_ready`, `cap_table_ready`, `site_preview`, `qa_report`, `deploy_status`, `guide_ready` render as compact cards with a button that opens the matching workspace tab.
2. Light markdown in content is rendered with `Markdown`; links open in a new tab; never raw JSON.
3. Composer: multiline input, Enter sends, Shift+Enter newline, disabled while sending; a typing indicator with the expected agent's identity (the active agent) appears while the request is in flight; suggested replies on the latest agent message are buttons that send their text.
4. New messages are announced politely (`aria-live`), the list auto-scrolls only when the user is at the bottom ("New messages" pill otherwise); the active agent is shown in the panel header.
5. `open_view` from the API switches the workspace tab on desktop and shows a "View in workspace" button on phones.
6. Errors (e.g. API down) show a friendly inline error with retry, and the unsent text is kept.
7. Jobs and notices: when a response starts a job (website build/deploy), the chat shows a progress card that follows `useJob` (queued -> running -> done or failed with a friendly retry) and the QA/preview messages appear when it finishes; the PII-removal and AI-allowance notices render as calm notice cards (the allowance one with a "See plans" button); a `plan_required` action reply shows the `PlanGate` prompt.
8. Overview: the six steps with `StatusBadge` and detail, overall percent, 83(b) deadline with a `Countdown` (warning tone under 8 days, danger when passed), company name, entity and state, founders with equity, and "what's next" suggestions; empty state for a new case.
9. Component tests (vitest) cover the message types, the composer, suggested replies, job cards, notices and the Overview states (incl. the team strip: members and pending invites, with a link to the Team view).
10. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading (skeleton), empty and error states on both views, no layout shift, friendly copy.
11. **Playwright screenshots** in `evidence/T-018/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-018/feature_run.py`)

Builds the frontend; with `running_app(seed_stage="new")`, logged in as Alice through the login page, drives a real conversation in
the browser: sends the business description, founders (with the equity mistake ->
validation message visible), asks "LLC or C-Corp?" (asserts the "Manager brought in the
Law Agent" banner and a message labelled "Law Agent"), asks for names (return + handover
banners), clicks a suggested reply; asserts the typing indicator appears during a send.
Asks the Website Agent for a site (with `seed_stage="names"`) and asserts the job card progresses to done. Then with `seed_stage="legal"` opens Overview and asserts the step badges and the 83(b)
countdown. Saves screenshot matrices `chat` and `overview`, checks no horizontal scroll and
no raw JSON, and shows the error state by opening a company Alice does not belong to (friendly not-found).

## Out of scope

Other workspace views (T-019–T-022); shared components (T-011, report `BLOCKED` if one is missing).
