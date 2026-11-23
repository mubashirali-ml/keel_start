# T-040: HTTP API: plans, Stripe checkout and portal, webhook, test checkout, and the admin endpoints

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-029, T-030, T-032, T-038 |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0033](../docs/adr/0033-security-hardening.md) |
| **Status** | todo |

## Goal

Over HTTP, anyone can see the plans, a logged-in founder can start Stripe Checkout and
open the billing portal, Stripe's webhook keeps subscriptions in sync, the in-app test
checkout works when payments are simulated, and admins can read the admin pages and
retry failed jobs.

## Owns (only these paths may change)

- `launch_agents/api/routes/billing.py`
- `launch_agents/api/routes/admin.py`
- `tests/test_api_billing.py`
- `tests/test_api_admin.py`
- `evidence/T-040/`
- `prs/T-040.md`

## Contracts

- **Provides:** the T-040 rows of the ADR-0032 table, as changed by ADR-0038 (`GET /api/billing/subscription` returns `BillingOverview`, new `POST /api/billing/change-plan`, admin `users?plan=` filter and `price_checks` in system info), as `router = APIRouter()` in each file.
- **Consumes:** `BillingService` (T-029), `AdminService` (T-038), `require_user` / `require_admin` (T-016 `api/deps.py`, same wave: tests use a minimal app with equivalent dependencies), `FakePaymentGateway` (T-001).

## Acceptance criteria

1. `GET /api/billing/plans` public; `GET /api/billing/subscription` for the user returns `BillingOverview`; `POST /api/billing/change-plan` `{plan, interval}` (CSRF) -> `Subscription`, 409 friendly without a paid subscription, 422 for `free`; `POST /api/billing/checkout` `{plan, interval}` -> `{url}`; `POST /api/billing/portal` -> `{url}` (409 friendly when never subscribed).
2. `POST /api/billing/webhook`: reads the raw body, verifies the signature (400 `webhook_invalid` on failure), is exempt from CSRF and session auth, returns 200 for processed and duplicate events, and is idempotent; body limit 256 KB.
3. `POST /api/billing/test-checkout/{session_id}/complete` works only with the fake gateway (403 otherwise) and only for the user who started that session; afterwards `GET /api/auth/me` (when T-039 is merged) or `GET /api/billing/subscription` shows Launch; a following `change-plan` to `team` shows Team.
4. Admin routes require `is_admin` (403 for others, 401 logged out); paging and filters per ADR-0034 plus `GET /api/admin/users?plan=team` (ADR-0038); `/api/admin/system` includes `price_checks`; `POST /api/admin/jobs/{id}/retry` re-queues; no admin response contains chat text, document content or website content (asserted against the response schemas).
5. Routes contain no business logic.

## Feature run (`evidence/T-040/feature_run.py`)

Over `TestClient` with the fake gateway: lists plans; Alice starts checkout (prints the
test-checkout URL), completes it and prints her billing overview, switches to Team and
prints it again; posts a forged webhook
(400) and a replayed one (200, no change); opens the portal URL; then as an admin lists
users, companies, usage, failed jobs and emails, retries a failed job and prints the
system info; shows a non-admin's 403.

## Out of scope

Pricing and billing screens (T-043, T-044), admin screens (T-045).
