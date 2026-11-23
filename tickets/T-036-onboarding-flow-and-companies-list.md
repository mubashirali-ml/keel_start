# T-036: Onboarding flow and companies list: describe your company, meet your agents, start

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-039, T-041 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

Right after signing up, a founder is guided in three calm steps (describe your company,
meet your agents, start the conversation) into their first company, and returning
founders land on a clear list of their companies with progress and the next step for each.

## Owns (only these paths may change)

- `frontend/src/features/onboarding/`
- `evidence/T-036/`
- `prs/T-036.md`

## Contracts

- **Provides:** `CompaniesPage`, `OnboardingPage` (named exports, ADR-0035).
- **Consumes:** `@/design`, `@/agents` (identities), `@/brand`, `@/api` (`useCases`, `useCreateCase`, `usePostMessage`, `useAgents`, `useMe`, `PlanGate`) (T-011); endpoints from T-041.

## Acceptance criteria

1. Onboarding step 1 "Describe your company": one textarea with an example placeholder and three example chips ("Bookkeeping software for bakeries", ...); step 2 "Meet your agents": a card per agent from `/api/agents` (icon, accent, name, one-line role, "deterministic" badge for Cap Table and Sign-off) and the not-legal-advice line; step 3 creates the company, posts the description as the first chat message, and opens the workspace with the chat focused.
2. A step indicator shows 1/2/3; Back works; the description survives a reload (session storage, wrapped in try/catch).
3. Companies list: card per company with name (or "New company"), progress bar and percent, the next step in plain words (from the case view's progress), role badge (Owner / Member), last activity; "New company" button wrapped in `PlanGate` when the plan's company limit is reached; empty state that starts onboarding.
4. First-time users (no companies) are sent from `/app` to `/app/onboarding`.
5. Errors (create fails, API down) keep the typed description and offer Retry.
6. Component tests cover the three steps, reload persistence, the plan gate on "New company" and the empty state.
7. **Quality bar:** responsive at 390px with no horizontal page scroll, light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-036/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-036/feature_run.py`)

With `running_app(seed_stage="account", plan="free")`: Alice logs in, is sent to
onboarding, completes the three steps and asserts the Manager's reply in the workspace
chat; returns to `/app` and asserts the company card with progress; tries "New company"
and asserts the plan gate. With `seed_stage="complete"` asserts a 100 % card. Saves
matrices `onboarding-describe`, `onboarding-agents`, `companies`; checks no horizontal
scroll and no raw JSON.

## Out of scope

Sign-up itself (T-042), the chat view (T-018), billing (T-044).
