# T-038: Admin service and CLI: customers, companies, plans, AI usage, failed jobs and emails

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-005, T-026, T-027, T-028, T-029, T-030, T-032 |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0033](../docs/adr/0033-security-hardening.md) |
| **Status** | todo |

## Goal

The owner can run the business: see customers, companies, plans, AI usage against plan
limits, failed jobs (and retry them) and failed emails, check the system's configuration
at a glance, and grant admin rights from the command line, without ever seeing customers'
chat, documents or websites.

## Owns (only these paths may change)

- `launch_agents/admin/`
- `launch_agents/persistence/admin.py`
- `tests/test_admin.py`
- `evidence/T-038/`
- `prs/T-038.md`

## Contracts

- **Provides:** `AdminService` (every method of ADR-0034, with the ADR-0038 additions: `users(*, query, page, plan=None)` and a constructor keyword `price_checks: Callable[[], list[PriceCheck]] | None = None`), `AdminQueries`, row models `AdminUserRow`, `AdminCaseRow`, `AdminUsageRow`, `OutboxEmailRow`, `Page[T]`, `SystemInfo`; CLI `python -m launch_agents.admin grant-admin <email> | revoke-admin <email>`.
- **Consumes:** `AccountsRepository` (T-026), `TeamRepository` (T-027), `BillingRepository` (T-029), `JobsRepository` / `JobRunner.retry` (T-030), `LimitsRepository` usage counts (T-032), `EmailOutboxRepository` (T-028), `schema_is_current` (T-005), `Settings` (T-001).

## Acceptance criteria

1. `users`: search by email/name, 25 per page, with created, verified, plan (Free, Launch or Team) and support level, number of companies, last seen, filterable by plan so Team customers' support mail can be answered first; `companies`: name, member count, created, milestone flags (facts locked, documents executed, site published), billing plan; both sorted newest first.
2. `usage(month)`: per user calls and tokens for the month against the plan limit, highest first.
3. `jobs(status)` and `emails(status)` page through records; email recipients are masked; job errors show the friendly message only.
4. `retry_job` re-queues a failed job and writes an `admin_audit` row with the admin's id; retrying a non-failed job -> `InvalidStateError`.
5. `system()` reports LLM provider and per-agent models, domain checker, hosting (configured or not), email provider, payments mode (fake / Stripe test / Stripe live), migration status, the last worker heartbeat and `price_checks` (each paid plan and interval, flagged when Stripe's amount differs from the settings; empty when no callable is given); never a secret value.
6. **No content access:** no `AdminService` method returns chat text, document content, website content or facts beyond the company name (a test inspects every row model's fields).
7. CLI `grant-admin` / `revoke-admin` change `is_admin`, print a confirmation, and exit non-zero for an unknown email; each change is written to `admin_audit` with admin id "cli".

## Feature run (`evidence/T-038/feature_run.py`)

Seeds a temp database with three users on Free, Launch and Team, companies, LLM usage rows,
one failed job and one failed email; prints each admin page as a table, retries the
failed job (status printed), prints `SystemInfo`, and runs the CLI to grant and revoke
admin rights, printing its output and exit codes.

## Out of scope

Admin HTTP routes (T-040) and screens (T-045).
