# T-045: Admin area screens: customers, companies, AI usage, failed jobs, emails and system status

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-011, T-016, T-040 |
| **ADRs** | [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0035](../docs/adr/0035-frontend-v2-brand-routes-layout-and-feature-boundaries.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

The owner opens a small, fast admin area to see customers, companies and plans, AI
usage against plan limits, failed jobs (with retry) and failed emails, and the system's
configuration, without access to any customer's content.

## Owns (only these paths may change)

- `frontend/src/features/admin/`
- `evidence/T-045/`
- `prs/T-045.md`

## Contracts

- **Provides:** `AdminPage` with sections `users`, `companies`, `usage`, `jobs`, `emails`, `system` (named export, ADR-0035).
- **Consumes:** `@/design` (`Table`, `Tabs`, `Badge`, `ConfirmDialog`), `@/api` admin hooks (T-011); endpoints from T-040.

## Acceptance criteria

1. Section tabs with URL state; each list has search (users, companies), status filter (jobs, emails), paging, loading skeletons, empty states and error states.
2. Users: email, name, verified, plan badge, companies, created, last seen. Companies: name, members, milestone chips, plan, created. Usage: month picker, per-user calls/tokens with a bar against the plan limit (warning tone above 80 %).
3. Jobs: kind, company, status, attempts, friendly error, updated; "Retry" with confirmation updates the row. Emails: masked recipient, template, status, error, time.
4. System: provider names and per-agent models, domain checker, hosting configured, email provider, payments mode, migration status, last worker heartbeat (stale shown in danger tone).
5. A banner states "Admins see account metadata only; company content stays private." No view renders chat, document or website content.
6. Non-admins get the friendly "not available" page (from T-011) and the API's 403.
7. Component tests cover filters, paging, retry confirmation and the usage bar thresholds.
8. **Quality bar:** responsive at 390px with no horizontal page scroll (tables stack), light and dark mode, keyboard accessible with visible focus, WCAG AA contrast, loading/empty/error states, no layout shift, friendly copy.
9. **Playwright screenshots** in `evidence/T-045/` at 1280px and 390px, light and dark.

## Feature run (`evidence/T-045/feature_run.py`)

With `running_app(seed_stage="website")` and Alice granted admin through the CLI before
start, plus a failed job and a failed email inserted through the services: logs in, opens
each admin section and asserts rows; retries the failed job and asserts its new status;
checks the system section values; logs in as Bob (not admin) and asserts the not-available
page. Saves matrices `admin-users`, `admin-jobs`, `admin-system`; checks no horizontal
scroll and no raw JSON.

## Out of scope

Admin endpoints and service (T-040, T-038).
