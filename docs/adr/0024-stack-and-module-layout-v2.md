# ADR-0024: Stack and module layout v2 (sellable product)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | all (T-001 creates the layout) |
| **Scope** | `launch_agents/`, `migrations/`, `alembic.ini`, `tests/`, `pytest.ini`, `.env.example`, `frontend/`, `demo/`, deployment files |

## Context

ADR-0007 fixed a FastAPI + SQLite backend with no accounts. The brief now makes the
product sellable: accounts and co-founder invites, authorization on every endpoint,
electronic signatures with signed PDFs, Stripe billing, transactional email, PostgreSQL
with versioned migrations, Docker, CI, security hardening, an admin area, tracked
background jobs and a demo video. The cross-cutting contracts must exist in wave 0 so
that later waves add features without refactoring earlier ones. This ADR **supersedes
ADR-0007**. Its import rules, test conventions and "T-001 stubs everything" rule carry over.

## Decision

### Stack

| Concern | Choice |
|---|---|
| HTTP API | FastAPI + uvicorn, app factory `launch_agents.api.app:create_app` |
| Database | SQLAlchemy 2.0; **PostgreSQL** (psycopg 3) in production, **SQLite** for development and tests; **Alembic** migrations (ADR-0027) |
| Types | pydantic v2 (ADR-0008 + the new contracts in ADR-0026, ADR-0028–ADR-0031) |
| Turn graph | LangGraph, no checkpointer (ADR-0009) |
| LLM | five providers behind one interface (ADR-0022) |
| Outbound HTTP | httpx with explicit timeouts (ADR-0023) |
| Passwords | argon2id (`argon2-cffi`) (ADR-0026) |
| Payments | Stripe (`stripe` SDK) behind a port (ADR-0030) |
| Email | stdlib `smtplib` behind a port (ADR-0029) |
| PDF / DOCX | `reportlab` (signed PDF), `python-docx` (editable copy) (ADR-0031) |
| Jobs | our own DB-backed queue + worker, no broker (ADR-0028) |
| Deployment | Docker image + compose, GitHub Actions CI (ADR-0034) |

The complete dependency list is ADR-0025. No other package may be imported.

### Python package layout (owner tickets)

```
launch_agents/
  config.py                    Settings, load_settings, ConfigError (ADR-0021)            T-001
  reliability.py               RetryPolicy, call_with_retry, Deadline (ADR-0023)          T-001
  domain/                      shared types (ADR-0008 + ADR-0026/0028/0029/0030/0031)     T-001
  llm/provider.py fake.py usage.py __init__.py                                             T-001
  llm/claude_code.py           ClaudeCodeProvider (ADR-0022)                              T-024
  llm/anthropic_provider.py, llm/openai_compat.py                                         T-025
  ports/                       DomainChecker, SiteHost, EmailSender, Mailer, Notifier,
                               PaymentGateway, EntitlementsProvider, JobRunner + fakes    T-001
  adapters/rdap.py                                                                        T-007
  adapters/netlify.py                                                                     T-008
  adapters/smtp_email.py                                                                  T-028
  adapters/stripe_payments.py                                                             T-029
  rules/validation.py | rules/cap_table.py, rules/exports.py                              T-002 | T-003
  signoff/                     state machine with signature evidence (ADR-0014, ADR-0031) T-004
  persistence/tables.py        every table (ADR-0027)                                     T-001
  persistence/engine.py, persistence/repository.py   engine, init_db, case Repository     T-005
  persistence/accounts.py      users, sessions, auth tokens                               T-026
  persistence/team.py          memberships, invites                                       T-027
  persistence/email_outbox.py                                                             T-028
  persistence/billing.py       subscriptions, billing events                              T-029
  persistence/jobs.py          jobs, worker heartbeats                                    T-030
  persistence/limits.py        rate-limit counters, LLM usage                             T-032
  persistence/privacy.py       export + delete queries                                    T-037
  persistence/admin.py         admin read models                                          T-038
  accounts/                    passwords, sessions, AuthService (ADR-0026)                T-026
  team/                        TeamService: members, invites                              T-027
  access/                      authorize_case, permissions (ADR-0026)                     T-027
  email/                       templates, OutboxMailer, send job (ADR-0029)               T-028
  billing/                     plans, entitlements, BillingService (ADR-0030)             T-029
  jobs/                        DbJobRunner, Worker, Scheduler, CLI (ADR-0028)             T-030
  pdf/                         signed PDF + DOCX rendering (ADR-0031)                     T-031
  security/                    CSRF, headers, rate limits, metered LLM, PII scrub (ADR-0033) T-032
  observability/               JSON logs, request ids, error hook (ADR-0034)              T-033
  agents/base.py, agents/manager/greeting.py, agents/*/fake.py (empty)                     T-001
  agents/law/ name/ website/ qa/ guide/ | agents/manager/                                 T-006..T-010 | T-012
  orchestrator/                                                                           T-012
  pipelines/website.py, workflows/website.py                                              T-013
  workflows/case.py | workflows/legal.py                                                  T-014 | T-015
  workflows/ports.py           service protocols (ADR-0032)                               T-001
  notifications/               EmailNotifier, 83(b) reminder sweep (ADR-0029)             T-035
  privacy/                     data export, account deletion                              T-037
  admin/                       AdminService, `python -m launch_agents.admin`              T-038
  composition.py               build_services(settings) composition root                  T-016
  api/app.py errors.py deps.py middleware.py schemas.py routes/__init__.py                T-016
  api/routes/cases.py, api/routes/jobs.py                                                 T-041
  api/routes/legal.py, api/routes/website.py                                              T-017
  api/routes/auth.py, api/routes/account.py, api/routes/team.py                           T-039
  api/routes/billing.py, api/routes/admin.py                                              T-040
  demo/                        seeded demo companies + demo users (ADR-0036)              T-016
  devtools/                    Playwright app-launch helpers (ADR-0036)                   T-011
migrations/, alembic.ini       Alembic env + 0001_initial (ADR-0027)                      T-001
```

Top level: `frontend/` (T-011, ADR-0035), `demo/` (the demo video, T-046, ADR-0037),
`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/` (T-034, ADR-0034).

**T-001 creates every Python file above** with the exact signatures and docstrings of
the ADRs; behaviour owned by later tickets raises `NotImplementedError`. Each package's
`__init__.py` (written by T-001) re-exports its public names and is not changed later.

### Import direction (a reviewer checks it)

```
domain  <-  config, reliability  <-  llm, ports  <-  rules, signoff, persistence, accounts, team, access,
            email, billing, jobs, pdf, security, observability, agents/*  <-  orchestrator, pipelines
        <-  workflows, notifications, privacy, admin  <-  composition  <-  api, demo
```

- `domain` imports nothing from the package. Agents never import `persistence`,
  `workflows`, `api` or any account/billing module; they get `AgentContext` (ADR-0009).
- Services receive the caller as a `CaseAccess` / `RequestContext` (ADR-0026); they never
  read HTTP objects. Only `api/` knows about requests, cookies and headers.
- Only `composition.py` chooses concrete providers and adapters from `Settings`.

### Tests

As in ADR-0007: all Python tests in `tests/`, one file per area named by the owning
ticket; `pytest.ini` and `tests/conftest.py` belong to T-001. Additional shared fixtures
(T-001): `settings` (test settings map), `engine` (fresh SQLite file migrated to head;
skips if persistence is still a stub), `inline_jobs`, `fake_mailer`, `fake_notifier`,
`fake_payments`, `entitlements_launch` / `entitlements_free`, `request_ctx(user=...)`,
`system_access(case_id)`. No test touches the network. Postgres-only tests run when
`LAUNCH_TEST_POSTGRES_URL` is set (CI) and are skipped otherwise.

### Running

```
bash scripts/py.sh -m alembic upgrade head
bash scripts/py.sh -m uvicorn launch_agents.api.app:create_app --factory --port 8000
bash scripts/py.sh -m launch_agents.jobs worker        # production; development embeds a worker
cd frontend && npm run dev                              # Vite on 5173, proxies /api to 8000
docker compose up                                       # PostgreSQL + migrate + app + worker
```

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One package, layered modules, one owner per path, contracts in wave 0 (chosen) | Parallel waves without refactors; import rules checkable | Very large wave-0 stub set |
| B. Separate services (auth service, billing service) | Independent deploys | Operational overhead far beyond v1 |
| C. Add accounts later as middleware | Smaller wave 0 | Every service signature changes later; exactly the refactor the owner wants to avoid |

## Consequences

- Twenty wave-1 tickets can run in parallel because every boundary is a typed stub.
- T-001 grows again; it remains mechanical (types, fakes, stubs, one migration).
- Changing the module map or a cross-ticket signature needs a superseding ADR.
