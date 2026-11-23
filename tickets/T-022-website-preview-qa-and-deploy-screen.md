# T-022: Website screen: live preview, QA report, deploy status and download

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017 |
| **ADRs** | [ADR-0019](../docs/adr/0019-frontend-design-system-and-app-layout.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0020](../docs/adr/0020-ui-recorded-runs-and-demo-seeding.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

Founders preview their generated website, read the QA report (pass/fail per check, with
fix rounds), deploy it (or explicitly accept remaining issues), see the live URL or the
"deploy not configured" status, and download the site.

## Owns (only these paths may change)

- `frontend/src/features/website/`
- `evidence/T-022/`
- `prs/T-022.md`

## Contracts

- **Provides:** the Website page (default export).
- **Consumes:** `@/design`, `@/api` (`useWebsite`, `useBuildWebsite`, `useDeployWebsite`, `useCase`, preview/download URLs), `ActingFounderContext` (T-011); endpoints from T-017.

## Acceptance criteria

1. Preview: sandboxed iframe (`sandbox` without scripts) of the latest build's pages with a page switcher and desktop/phone width toggle; a skeleton while loading; build version shown.
2. QA report: overall pass/fail, a round selector (Round 0 = first check, then fixes), all ten checks with pass/fail icon + text, issues with page and message; a note when automatic fixes ran ("QA found 1 issue; the Website Agent fixed it in round 1").
3. Deploy: "Deploy site" when QA passed; when QA failed, the button opens a `ConfirmDialog` listing the remaining issues and requires an explicit "Deploy anyway as {acting founder}" (sends `override_qa`); status badge (deployed / failed / not configured) with the live URL as a link; the not-configured state explains that a hosting token is needed and that preview and download still work.
4. "Download site (.zip)" works in every state with a build; "Request changes" sends a message to the chat (pre-filled "@website ").
5. Empty state before any build (button that asks the Website Agent in the chat); `name_not_chosen` shows a friendly pointer to Names.
6. Component tests cover QA rendering per round, the override dialog, status states and empty state.
7. **Quality bar:** responsive at 390px with no horizontal page scroll (iframe scales), light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-022/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-022/feature_run.py`)

With `running_app(seed_stage="signed")`: opens Website (empty state), asks the Website
Agent in the chat to build the site with a Pricing page and testimonials, asserts the
preview iframe shows the company name, the QA report shows round 0 failing and round 1
passing, deploys and asserts the fake-host URL; then a second `running_app` with
`env={"HOSTING_PROVIDER": "none"}` (everything else still faked, ADR-0011) builds again
and asserts the "deploy not configured" status and a working download. Saves matrices `website`, `website-qa`;
checks no horizontal scroll and no raw JSON.

## Out of scope

Site generation and QA logic (T-008, T-009, T-013).
