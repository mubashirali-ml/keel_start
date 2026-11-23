# T-021: Cap Table screen: table, ownership chart, vesting timeline, downloads

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-017, T-039 |
| **ADRs** | [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

Founders see who owns what: a clear table of shares (or units), an ownership chart, each
founder's vesting timeline with the cliff, and CSV / Excel downloads.

## Owns (only these paths may change)

- `frontend/src/features/cap-table/`
- `evidence/T-021/`
- `prs/T-021.md`

## Contracts

- **Provides:** the Cap Table page (default export).
- **Consumes:** `@/design`, `@/api` (`useCapTable`, `useCase`, download URLs), `@/lib/format`, Recharts (T-011); endpoints from T-017.

## Acceptance criteria

1. Table: founder, email, equity %, shares/units (thousands separators, label from `unit_label`), vesting, cliff, fully-vested date; total row showing exactly 10,000,000; stacks into cards below 640px.
2. Ownership donut chart (Recharts) using agent-neutral chart tokens with a legend and an accessible text alternative (a visually hidden table or `aria-label` summary).
3. Vesting timeline: per founder, cumulative vested over months with the cliff marked ("Cliff: 12 months — 1,200,000 shares vest"), today's position marked, and a founder selector; readable in dark mode.
4. Download CSV / Download Excel buttons hit the API download URLs.
5. Facts not ready (409) shows a friendly empty state naming what is missing (from the case view), not an error.
6. Component tests cover number formatting, total row, unit label (LLC units vs. C-Corp shares), the empty state and chart accessibility text.
7. **Quality bar:** responsive at 390px with no horizontal page scroll (chart resizes), light and dark mode, keyboard accessible with visible focus, WCAG AA contrast (chart colors too), loading/empty/error states, no layout shift, friendly copy.
8. **Playwright screenshots** in `evidence/T-021/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-021/feature_run.py`)

With `running_app(seed_stage="new")`, logged in as Alice through the login page: opens Cap Table and asserts the friendly not-ready
state. With `seed_stage="facts"`: asserts Alice 6,000,000 and Bob 4,000,000 units, total
10,000,000, the cliff marker text, switches the vesting founder; clicks both downloads
(Playwright `expect_download`) and checks the CSV header and the XLSX file signature.
Saves the matrix `cap-table`; checks no horizontal scroll and no raw JSON.

## Out of scope

Cap table calculations (T-003); documents (T-020).
