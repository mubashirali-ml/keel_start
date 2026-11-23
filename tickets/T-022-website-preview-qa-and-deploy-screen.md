# T-022: Website screen: live preview, QA report, deploy status and download

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017, T-039, T-041 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md) |
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
- **Consumes:** `@/design`, `@/api` (`useWebsite`, `useBuildWebsite`, `useDeployWebsite`, `useCase`, preview/download URLs), `useJob`, `useMe`, `PlanGate` (T-011); endpoints from T-017.

## Acceptance criteria

1. Preview: sandboxed iframe (`sandbox` without scripts) of the latest build's pages with a page switcher and desktop/phone width toggle; a skeleton while loading; build version shown.
2. QA report: overall pass/fail, a round selector (Round 0 = first check, then fixes), all ten checks with pass/fail icon + text, issues with page and message; a note when automatic fixes ran ("QA found 1 issue; the Website Agent fixed it in round 1").
3. Deploy: "Deploy site" when QA passed; when QA failed, the button opens a `ConfirmDialog` listing the remaining issues and requires an explicit "Publish anyway" confirmation naming the logged-in founder (sends `override_qa`); on the Free plan the publish button is wrapped in `PlanGate` ("Publishing is part of the Launch plan"); status badge (deployed / failed / not configured) with the live URL as a link; the not-configured state explains that a hosting token is needed and that preview and download still work.
4. "Download site (.zip)" works in every state with a build; "Request changes" sends a message to the chat (pre-filled "@website ").
5. Builds and deploys are jobs: after "Build" or "Publish" a progress panel follows `useJob` (queued, building, QA round n, publishing) with no hung spinner; a failed job shows its friendly error and a Retry button; leaving and returning to the page resumes the progress from `active_jobs`.
6. Empty state before any build (button that asks the Website Agent in the chat); `name_not_chosen` shows a friendly pointer to Names.
7. Component tests cover QA rendering per round, the override dialog, job progress, the plan gate, status states and empty state.
8. **Quality bar:** responsive at 390px with no horizontal page scroll (iframe scales), light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
9. **Playwright screenshots** in `evidence/T-022/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-022/feature_run.py`)

With `running_app(seed_stage="signed")`, logged in as Alice through the login page: opens Website (empty state), asks the Website
Agent in the chat to build the site with a Pricing page and testimonials, asserts the
preview iframe shows the company name, the QA report shows round 0 failing and round 1
passing, deploys and asserts the fake-host URL; then a second `running_app` with
`env={"HOSTING_PROVIDER": "none"}` (everything else still faked, ADR-0011) builds again
and asserts the "deploy not configured" status and a working download; a third run with `plan="free"` asserts the plan gate on Publish. Saves matrices `website`, `website-qa`;
checks no horizontal scroll and no raw JSON.

## Out of scope

Site generation and QA logic (T-008, T-009, T-013).
