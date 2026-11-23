# T-018: Chat experience and Overview screen

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017 |
| **ADRs** | [ADR-0019](../docs/adr/0019-frontend-design-system-and-app-layout.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md), [ADR-0018](../docs/adr/0018-frontend-stack-and-npm-package-set.md) |
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
- **Consumes:** `@/design`, `@/agents`, `@/api` hooks (`useMessages`, `usePostMessage`, `useCase`), `ActingFounderContext` (T-011); endpoints from T-016.

## Acceptance criteria

1. Messages render per role: founder bubbles (right, with the acting founder's name), agent messages (left) with `AgentAvatar`, display name and accent; `handoff` messages render as a centered inline banner ("Manager brought in the Law Agent" / "… handed the conversation back to the Manager"); `validation` messages list issues clearly; `name_options`, `documents_ready`, `cap_table_ready`, `site_preview`, `qa_report`, `deploy_status`, `guide_ready` render as compact cards with a button that opens the matching workspace tab.
2. Light markdown in content is rendered with `Markdown`; links open in a new tab; never raw JSON.
3. Composer: multiline input, Enter sends, Shift+Enter newline, disabled while sending; a typing indicator with the expected agent's identity (the active agent) appears while the request is in flight; suggested replies on the latest agent message are buttons that send their text.
4. New messages are announced politely (`aria-live`), the list auto-scrolls only when the user is at the bottom ("New messages" pill otherwise); the active agent is shown in the panel header.
5. `open_view` from the API switches the workspace tab on desktop and shows a "View in workspace" button on phones.
6. Errors (e.g. API down) show a friendly inline error with retry, and the unsent text is kept.
7. Overview: the six steps with `StatusBadge` and detail, overall percent, 83(b) deadline with a `Countdown` (warning tone under 8 days, danger when passed), company name, entity and state, founders with equity, and "what's next" suggestions; empty state for a new case.
8. Component tests (vitest) cover the message types, the composer, suggested replies and the Overview states.
9. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading (skeleton), empty and error states on both views, no layout shift, friendly copy.
10. **Playwright screenshots** in `evidence/T-018/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-018/feature_run.py`)

Builds the frontend; with `running_app(seed_stage="new")` drives a real conversation in
the browser: sends the business description, founders (with the equity mistake ->
validation message visible), asks "LLC or C-Corp?" (asserts the "Manager brought in the
Law Agent" banner and a message labelled "Law Agent"), asks for names (return + handover
banners), clicks a suggested reply; asserts the typing indicator appears during a send.
Then with `seed_stage="legal"` opens Overview and asserts the step badges and the 83(b)
countdown. Saves screenshot matrices `chat` and `overview`, checks no horizontal scroll and
no raw JSON, and shows the error state by opening a non-existent case.

## Out of scope

Other workspace views (T-019–T-022); shared components (T-011, report `BLOCKED` if one is missing).
