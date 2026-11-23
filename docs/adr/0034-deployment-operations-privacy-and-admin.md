# ADR-0034: Deployment, operations, privacy controls and the admin area

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-033 (logs, request ids, error hook), T-034 (Docker, compose, CI, operations guide), T-037 (export + delete), T-038 (admin service + CLI), T-040 (admin routes), T-044/T-045 (screens) |
| **Scope** | `launch_agents/observability/`, `launch_agents/privacy/`, `launch_agents/admin/`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/`, `docs/operations.md` |

## Context

The brief: Docker images and a compose file; health and readiness endpoints; all config
from the environment; CI that runs the same checks as the merge gate; structured logs
with request ids; pluggable error reporting; a small admin area (customers, companies,
plan, LLM usage, failed jobs); documented backups; customers can export all their data
and delete their account.

## Decision

### Observability (`observability/`, T-033)

```python
def configure_logging(settings: Settings) -> None        # JSON (production) or text; redaction filter (ADR-0033)
class RequestContextMiddleware:                          # ASGI: X-Request-ID in/out (accepts [A-Za-z0-9-]{8,64}),
                                                         # binds request_id/user_id/case_id to a ContextVar, logs one
                                                         # line per request: method, route, status, duration_ms
def log_context(**fields) -> ContextManager[None]
ErrorReporter = Callable[[BaseException, Mapping[str, Any]], None]
def load_error_reporter(dotted: str | None) -> ErrorReporter   # "pkg.module:function"; default logs at ERROR
def report_error(exc: BaseException, **context) -> None        # never raises
```

Unhandled exceptions in requests and jobs call `report_error` with request id, route,
user id and job id (never bodies). The 500 body includes `request_id` so support can find it.

### Health and readiness (T-016 routes, checks here)

`GET /api/health` -> 200 `{status: "ok"}` while the process runs. `GET /api/ready`
checks: database reachable; `schema_is_current` (ADR-0027); in production a worker
heartbeat within 120 s; returns 503 with the failing check names (no secrets, no versions).

### Docker and compose (T-034)

- `Dockerfile`, multi-stage: `node:20-alpine` builds `frontend/dist`; `python:3.12-slim`
  runtime installs `requirements.txt`, copies `launch_agents/`, `migrations/`,
  `alembic.ini` and the built frontend, runs as a non-root user, `EXPOSE 8000`,
  `HEALTHCHECK` on `/api/health`, default command
  `uvicorn launch_agents.api.app:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers`.
  Playwright browsers are not in the production image.
- `docker-compose.yml`: `db` (postgres:16, named volume, healthcheck), `migrate`
  (same image, `alembic upgrade head`, runs once), `app` (depends on migrate, port 8000),
  `worker` (same image, `python -m launch_agents.jobs worker`); every service reads
  `.env`; `APP_ENV=production` only when the owner sets it.
- `.dockerignore` excludes `.venv`, `node_modules`, `.worktrees`, `evidence`, `demo/output`, `*.db`, `.env`.

### CI (`.github/workflows/ci.yml`, T-034)

On push and pull request: (1) backend tests on SQLite; (2) backend tests on PostgreSQL
16 (service container, `LAUNCH_TEST_POSTGRES_URL`), including Alembic upgrade ->
downgrade -> upgrade; (3) frontend `npm ci`, `npm run build`, `npm test`;
(4) every recorded feature run `evidence/T-*/feature_run.py` with `LAUNCH_FAKE_SERVICES=1`
after `playwright install --with-deps chromium` (the same checks the merge gate runs,
ADR-0003/ADR-0005); (5) `docker build`. Python 3.12, Node 20. No secrets needed.

### Privacy: export and delete (`privacy/`, T-037)

```python
class PrivacyService:
    def __init__(self, queries: PrivacyQueries, repo: Repository, team: TeamRepository,
                 accounts: AccountsRepository, billing: BillingService, settings: Settings, *, clock=utcnow) -> None
    def export_zip(self, user: User) -> tuple[str, bytes]
    def delete_account(self, user: User, *, password: str, confirm: str) -> DeletionReport
```

- **Export** (`{brand}-export-{date}.zip`): `account.json` (profile, plan, subscription
  status, sessions summary), and per company the user belongs to: `company.json`
  (facts, state, members), `chat.json`, `documents/` (every version as Markdown, signed
  PDFs of executed ones), `signatures.json`, `audit.json`, `cap-table.csv`,
  `checklist.json`, `website/` (latest bundle). Never another customer's data,
  never password hashes or tokens.
- **Delete** (password re-entry and typing `DELETE`): cancel the Stripe subscription
  immediately; for each company: if the user is the **only member**, delete the company
  and everything in it; otherwise remove the membership, pass ownership and billing to
  the longest-standing remaining member, and keep the company for the co-founders
  (default pending open question Q-008). Executed documents and their signature records
  stay with the remaining co-founders as the legal record (the deleted user's account
  link is set to NULL, the typed name and timestamp stay). Then delete sessions, tokens,
  outbox rows and the user. The report says what was deleted and kept.

### Admin area (`admin/`, T-038; routes T-040; screens T-045)

```python
class AdminService:
    def __init__(self, queries: AdminQueries, jobs: JobRunner, accounts: AccountsRepository, *, clock=utcnow) -> None
    def users(self, *, query: str | None, page: int) -> Page[AdminUserRow]      # email, name, created, verified, plan, companies, last seen
    def companies(self, *, query: str | None, page: int) -> Page[AdminCaseRow]   # name, members, created, milestones, plan
    def usage(self, *, month: str) -> list[AdminUsageRow]                        # user, calls, tokens in/out, limit
    def jobs(self, *, status: JobStatus | None, page: int) -> Page[JobRecord]
    def emails(self, *, status: str | None, page: int) -> Page[OutboxEmailRow]   # recipient masked, template, status, error
    def system(self) -> SystemInfo                                               # providers, configured services, migration head, worker heartbeat
    def retry_job(self, admin: User, job_id: str) -> JobRecord                    # audited in admin_audit
# CLI: python -m launch_agents.admin grant-admin <email> | revoke-admin <email>
```

Admins see **metadata only**: no chat text, document content or website content, which
keeps customer data private and is stated on the Privacy page. Admin is a flag on the
user set only from the CLI; every admin action is written to `admin_audit`.

### Backups (`docs/operations.md`, T-034)

Daily `pg_dump --format=custom` of the production database, kept 30 days off-host;
monthly restore test into a scratch database; documented restore steps; secrets kept in
the host's secret store, rotated by redeploying; uploads are not stored (nothing else to
back up). The guide also covers first deploy, `alembic upgrade head`, granting the first
admin, Stripe webhook setup and SMTP setup.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One image for app/worker/migrate + compose + GitHub Actions (chosen) | Simple to run anywhere Docker runs; CI mirrors the gate | No orchestration (Kubernetes) in v1 |
| B. Platform-specific deploy (Render, Fly) only | Less to write | Locks the owner to one host |
| C. Admins can read company content | Easier support | Privacy risk; customers would not trust it |

## Consequences

- The owner can deploy with `docker compose up` on any host with PostgreSQL storage.
- Support works from metadata and request ids, not from reading customer documents.
