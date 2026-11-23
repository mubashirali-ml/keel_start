# T-005: Persistence: engine for SQLite and PostgreSQL, migrations, and the case Repository

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md) |
| **Status** | merged |

## Goal

Companies, the full chat history, documents with versions and e-signature evidence, the
audit log, checklist progress and website builds are saved and read back as domain
objects, on SQLite in development and PostgreSQL in production, with a database schema
that is created and upgraded only through versioned migrations.

## Owns (only these paths may change)

- `launch_agents/persistence/engine.py`
- `launch_agents/persistence/repository.py`
- `tests/test_persistence.py`
- `tests/test_migrations.py`
- `evidence/T-005/`
- `prs/T-005.md`

## Contracts

- **Provides:** `create_db_engine(url)`, `init_db(engine)` (Alembic upgrade head), `schema_is_current(engine)`; `Repository(engine)` with every ADR-0012 method as changed by ADR-0027 (`create_case(*, created_by, facts, state)`, `list_cases(case_ids)`, `set_billing_user`, `delete_case`, signature evidence in `save_document`) and `transaction()`.
- **Consumes:** `persistence/tables.py`, `migrations/` (T-001, not edited here), domain types and errors (T-001). Packages `alembic`, `psycopg` (ADR-0025).

## Acceptance criteria

1. `create_db_engine`: SQLite with `check_same_thread=False` and `PRAGMA foreign_keys=ON` on every connection, `sqlite://` with `StaticPool`; PostgreSQL with `pool_pre_ping` and a 15 s `statement_timeout`.
2. `init_db` runs the migrations to head and is idempotent; `schema_is_current` is True after it and False on an empty database.
3. `tests/test_migrations.py`: upgrade -> downgrade -> upgrade on SQLite; the autogenerate diff against `tables.py` is empty; the same tests run on PostgreSQL when `LAUNCH_TEST_POSTGRES_URL` is set (marker `postgres`, skipped otherwise).
4. A case with two founders, `Decimal` equity, `created_by`/`billing_user_id` and a non-default `CaseState` round-trips exactly; `list_cases(ids)` returns only those cases, newest first.
5. Messages: consecutive `seq` per case from 1, `after_seq` filtering, cases never share a sequence.
6. Documents: insert; update with the right `expected_version`; wrong one -> `StaleVersionError`; new versions write `document_versions`; only current-version signatures are returned, **with every evidence field** (typed name, consent version, hash, user id, IP, user agent, acted-by).
7. Audit order and filtering; `delete_document` keeps audit; checklist upserts; site builds round-trip with bundle and QA reports; `latest_site_build` picks the highest version.
8. `delete_case` removes the case and every case-owned row (messages, documents, versions, signatures, checklist, builds) through the cascade, on SQLite and PostgreSQL.
9. `transaction()` rolls back everything when the block raises; unknown ids raise `NotFoundError`; data survives a new `Repository` on the same file; ORM rows never escape the package.

## Feature run (`evidence/T-005/feature_run.py`)

Creates a temp SQLite file, runs `init_db`, prints the migration head and the table list;
stores a company created by a user id, three chat messages, a document at v1 with one
e-signature (evidence printed), then v2 (stale save rejected), audit entries, checklist
ticks and a site build; opens a **new** engine on the same file and prints everything read
back, asserting equality; deletes the company and prints the empty row counts. When
`LAUNCH_TEST_POSTGRES_URL` is set it repeats the round trip on PostgreSQL; otherwise it
prints that the PostgreSQL part was skipped.

## Out of scope

Account, team, billing, jobs, email and limits repositories (their own tickets), business
rules (T-004, services), schema changes (the schema is T-001's; no new migration here).
