# T-034: Deployment: Docker image, compose with PostgreSQL and worker, GitHub Actions CI, operations guide

| | |
|---|---|
| **Wave** | 4 |
| **Depends on** | T-005, T-016, T-030, T-033 |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0003](../docs/adr/0003-merge-gate-tests-and-recorded-run.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md) |
| **Status** | todo |

## Goal

The owner can run the product anywhere Docker runs, on PostgreSQL with a separate
background worker and a one-shot migration step, every push is checked by CI with the
same checks as the merge gate (on SQLite and PostgreSQL), and a plain operations guide
explains first deploy, configuration, backups and restores.

## Owns (only these paths may change)

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.github/`
- `docs/operations.md`
- `tests/test_deploy_files.py`
- `evidence/T-034/`
- `prs/T-034.md`

## Contracts

- **Provides:** the ADR-0034 Docker image (app, worker and migrate from one image), compose file, CI workflow `.github/workflows/ci.yml`, and `docs/operations.md`.
- **Consumes:** `create_app`, `/api/health`, `/api/ready` (T-016), `python -m launch_agents.jobs worker` (T-030), `alembic upgrade head` (T-001/T-005), `requirements.txt` and `frontend/` build (read only).

## Acceptance criteria

1. `Dockerfile`: multi-stage (Node 20 frontend build, Python 3.12 slim runtime), non-root user, no dev tools or Playwright browsers in the final image, `HEALTHCHECK` on `/api/health`, default command per ADR-0034, `--proxy-headers`; builds reproducibly from a clean checkout.
2. `docker-compose.yml`: `db` (postgres:16, volume, healthcheck), `migrate` (one-shot `alembic upgrade head`), `app` (depends on db healthy + migrate completed, port 8000), `worker` (`python -m launch_agents.jobs worker`); env from `.env`; no secrets in the file; `APP_ENV` left to `.env`.
3. `.dockerignore` excludes `.venv`, `node_modules`, `.worktrees`, `evidence`, `demo/output`, `*.db`, `.env`, `prs`.
4. CI (`ci.yml`): on push and pull request; jobs for backend tests on SQLite, backend tests on PostgreSQL 16 service with `LAUNCH_TEST_POSTGRES_URL` incl. the migration round trip, frontend `npm ci` / `build` / `test`, every `evidence/T-*/feature_run.py` with `LAUNCH_FAKE_SERVICES=1` after `playwright install --with-deps chromium`, and `docker build`; caching for pip and npm; Python 3.12, Node 20; no secrets required.
5. `tests/test_deploy_files.py` validates without Docker: the compose file parses (PyYAML is available transitively; skip with a reason if not), has the four services and healthchecks, the Dockerfile has a non-root `USER` and the expected `CMD`, the CI workflow has the five jobs.
6. `docs/operations.md`: requirements; first deploy step by step (copy `.env.example`, set production values, `docker compose up -d`, grant the first admin with the CLI); every production environment variable and where to get it (Anthropic key, SMTP, Stripe keys, the four price ids for Launch and Team monthly and yearly with the matching `PLAN_*` amounts, the customer portal settings (cancellation and invoices on), the webhook endpoint `/api/billing/webhook`, `SUPPORT_EMAIL`, `BRAND_NAME`, Netlify token, `SECRET_KEY` generation); how to change a price or an allowance (new Stripe price + two env values, then check the admin price checks); watching AI cost on the admin usage page (ADR-0038); TLS via a reverse proxy; upgrades (`migrate` runs first); backups (daily `pg_dump`, 30-day retention, monthly restore test) and restore steps; logs and request ids; what to do when readiness fails.

## Feature run (`evidence/T-034/feature_run.py`)

Prints the validated structure of the compose file, Dockerfile and CI workflow (from the
same checks as the tests). If `docker` is available: builds the image, starts the compose
stack with a throwaway `.env` (fake services, test env, local Postgres), waits for
`/api/ready`, prints health/readiness, runs one request through the app and shows the
worker processing a job, then tears everything down. If Docker is not available it prints
that the live part was skipped (the static checks still must pass).

## Out of scope

Application code, the root `README.md` (harness-owned), hosting-provider specific deploys.
