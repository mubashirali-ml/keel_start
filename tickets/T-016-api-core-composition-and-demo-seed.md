# T-016: Composition root, secured app factory, health and readiness, and demo seeding

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-012, T-013, T-014, T-015, T-024, T-025, T-026, T-027, T-028, T-029, T-030, T-032, T-033, T-035, T-037, T-038 |
| **ADRs** | [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md) |
| **Status** | todo |

## Goal

The backend runs as the real product: configuration picks every provider and adapter
with no code change, every request passes through request ids, security headers, CORS,
CSRF and the error envelope, the caller is resolved from the session for every route,
jobs run in the background, health and readiness are reported, and a one-command demo
seed creates users and a company at any stage of the journey.

## Owns (only these paths may change)

- `launch_agents/composition.py`
- `launch_agents/api/__init__.py`
- `launch_agents/api/app.py`
- `launch_agents/api/errors.py`
- `launch_agents/api/deps.py`
- `launch_agents/api/middleware.py`
- `launch_agents/api/schemas.py`
- `launch_agents/api/routes/__init__.py`
- `launch_agents/demo/`
- `tests/test_composition.py`
- `tests/test_api_app.py`
- `tests/test_api_routes_contract.py`
- `tests/test_demo_seed.py`
- `evidence/T-016/`
- `prs/T-016.md`

## Contracts

- **Provides:** `build_services(settings, *, jobs=None) -> Services` (ADR-0032 fields; wires `get_llm`, `MeteredLLM` per company through `agent_deps` / `llm_for`, the job registry with the website, email and reminder handlers, `DbJobRunner` or the injected runner, `OutboxMailer`, `EmailNotifier`, `DbEntitlements`, `RateLimiter`, every service); full `create_app(services=None, settings=None)` per ADR-0032 (middleware order, embedded worker + scheduler lifecycle, routers, SPA mount); `api/deps.py`: `get_services`, `get_ctx`, `require_user`, `require_admin`, `require_case(permission)`, `rate_limit(cls)`, `set_session_cookie`, `clear_session_cookie`; the public routes `GET /api/health`, `/api/ready`, `/api/config`, `/api/agents` (in `api/routes/__init__.py`); `seed_case(settings, stage, *, plan)`, `DEMO_STAGES`, `SeedResult`, CLI `python -m launch_agents.demo` (ADR-0036).
- **Consumes:** every wave-1 and wave-2 module (see Depends on); the routers of T-017, T-039, T-040, T-041 (same wave, included by name; empty until they merge, so tests here use a test router for route-level checks).

## Acceptance criteria

1. `build_services` selection: `LAUNCH_FAKE_SERVICES=1` / `APP_ENV=test` -> every fake (explicit `HOSTING_PROVIDER` still wins); `LLM_PROVIDER` per ADR-0022 (providers constructed, never called); `EMAIL_PROVIDER` (and `EMAIL_DROP_FILE` -> `FileDropEmailSender`, ADR-0029), `PAYMENTS_PROVIDER`, `DOMAIN_CHECKER`, `HOSTING_PROVIDER` per ADR-0021/0011; DB migrated via `init_db` outside production; production settings with fakes cannot be built (the `ConfigError` from settings).
2. `get_ctx` builds `RequestContext` from the `la_session` cookie (via `AuthService.resolve_session`), client IP honouring `TRUSTED_PROXY_COUNT`, user agent, and `X-Act-As-Founder` only when demo mode is on; `require_case(P)` calls `authorize_case` and returns `CaseAccess`; session cookie attributes per ADR-0033.
3. Middleware order per ADR-0032; every response has `X-Request-ID` and the security headers; unsafe requests without a valid CSRF token -> 403 `csrf_failed` (webhook exempt); CORS only for configured origins with credentials; chat requests time out at 100 s with a friendly 503.
4. Errors: every `LaunchError` -> envelope with its status; validation -> 422 `invalid_request` with a friendly message; unexpected -> 500 `internal` with `request_id` and the error reported through `report_error`; no stack trace in any body.
5. `/api/health` always 200; `/api/ready` 200 when the database is reachable and at the latest migration (and, in production, the worker heartbeat is fresh), else 503 with failing check names; `/api/config` returns `PublicConfig` (brand name, demo mode, payments test mode, hosting configured, plans, consent text) with no secrets.
6. `tests/test_api_routes_contract.py` walks every registered `/api` route of the assembled app (re-run automatically as later routers merge) and asserts: each route has an auth dependency or is in the public allow-list of ADR-0032; every unsafe method is CSRF-protected unless allow-listed; every `/api/auth/*` and LLM route declares a rate-limit class; OpenAPI field names of responses match the ADR-0032 views.
7. Embedded worker and scheduler start with the app when `JOBS_EMBEDDED_WORKER=1` and stop cleanly on shutdown; with an injected `InlineJobRunner` nothing starts.
8. `seed_case` produces every ADR-0036 stage through the real services with fakes (asserted: `account` two verified users and a Launch subscription; `facts` locked with Bob a linked member; `names` with the "Acme" check and a chosen name; `legal` with Alice's e-signatures and Bob's edit invalidating one; `signed` all executed; `website` deployed after one QA fix round; `complete` all checklist items ticked); refuses without fake services; the CLI prints the case id and user emails.

## Feature run (`evidence/T-016/feature_run.py`)

Starts `create_app` with `TestClient` and fake services on a temp DB: prints `/api/health`,
`/api/ready`, `/api/config`; shows a request id round trip, the security headers, a CSRF
rejection and a 401 on a protected test route; prints the route-contract report table
(route, auth, CSRF, rate-limit class); seeds every demo stage with `seed_case` and prints
each stage's progress percent, members and document statuses; starts the embedded worker
in a real uvicorn process for a few seconds and shows a job executed by it.

## Out of scope

The feature routers (T-017, T-039, T-040, T-041), the UI (wave 4), Docker and CI (T-034).
