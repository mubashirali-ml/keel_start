# ADR-0027: Persistence v2: PostgreSQL and SQLite, Alembic migrations, data model

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (tables, initial migration, repository stubs), T-005 (engine + case repository), T-026, T-027, T-028, T-029, T-030, T-032, T-037, T-038 (their repositories) |
| **Scope** | `launch_agents/persistence/`, `migrations/`, `alembic.ini` |

## Context

ADR-0012 fixed SQLite with `create_all` and no migrations. The brief now requires
PostgreSQL in production and SQLite for development and tests, through SQLAlchemy with
versioned migrations, plus tables for users, sessions, memberships, invites,
subscriptions, jobs, emails, usage and limits. Many wave-1 tickets need tables at the
same time; if each wrote its own migration, the Alembic revision chain would collide.
This ADR **supersedes ADR-0012**. Its rules carry over: pydantic objects are the only
thing crossing a repository boundary, nested state is JSON text, each method is its own
transaction, `repo.transaction()` groups writes, and the cap table is computed, not stored.

## Decision

### One schema, defined in wave 0

`persistence/tables.py` (T-001) declares **every** table below on one `MetaData` with a
naming convention for constraints. `migrations/versions/0001_initial.py` (T-001) creates
exactly that schema (hand-written, portable SQL types only: `String`, `Text`, `Integer`,
`BigInteger`, `Boolean`, `DateTime(timezone=True)`, `Date`). JSON lives in `Text`
columns. Timestamps are UTC. Ids are `String(40)` from `new_id(prefix)`.

| Table | Columns | Keys / indexes |
|---|---|---|
| `users` | id, email (unique, lower-case), full_name, password_hash, email_verified_at NULL, is_admin, created_at, updated_at | PK id; UNIQUE email |
| `sessions` | token_hash, user_id, created_at, last_seen_at, expires_at, revoked_at NULL, ip NULL, user_agent NULL | PK token_hash; idx user_id |
| `auth_tokens` | token_hash, user_id, purpose (`verify_email`/`password_reset`), created_at, expires_at, used_at NULL | PK token_hash; idx (user_id, purpose) |
| `cases` | id, created_at, updated_at, facts_json, state_json, **created_by** NULL, **billing_user_id** NULL | PK id; idx billing_user_id |
| `memberships` | case_id, user_id, role, founder_id NULL, joined_at | PK (case_id, user_id); UNIQUE (case_id, founder_id) |
| `invites` | id, case_id, email, founder_id NULL, token_hash, invited_by, created_at, expires_at, accepted_at NULL, revoked_at NULL | PK id; UNIQUE token_hash; idx case_id |
| `messages` | as ADR-0012 | PK id; UNIQUE (case_id, seq) |
| `documents`, `document_versions` | as ADR-0012 | as ADR-0012 |
| `signatures` | document_id, founder_id, version, signed_at, **user_id** NULL, **typed_name**, **consent_version**, **ip** NULL, **user_agent** NULL, **content_sha256**, **acted_by_user_id** NULL | PK (document_id, founder_id, version) |
| `audit_log`, `checklist_items`, `site_builds` | as ADR-0012 | as ADR-0012 |
| `subscriptions` | user_id, plan, interval NULL, status, current_period_end NULL, cancel_at_period_end, provider_customer_id NULL, provider_subscription_id NULL, updated_at | PK user_id; UNIQUE provider_customer_id |
| `billing_events` | id (provider event id), type, received_at, processed_at NULL, error NULL, payload_json | PK id |
| `jobs` | id, kind, status, case_id NULL, user_id NULL, payload_json, result_json NULL, error NULL, attempts, max_attempts, run_at, locked_by NULL, locked_until NULL, dedupe_key NULL, created_at, updated_at, finished_at NULL | PK id; idx (status, run_at); UNIQUE dedupe_key |
| `worker_heartbeats` | worker_id, last_seen_at | PK worker_id |
| `email_outbox` | id, to_email, template, subject, text_body, html_body, status (`queued`/`sent`/`failed`), attempts, user_id NULL, case_id NULL, dedupe_key NULL, provider_id NULL, error NULL, created_at, sent_at NULL | PK id; UNIQUE dedupe_key |
| `llm_usage` | id (autoincrement), user_id NULL, case_id NULL, task, provider, model NULL, input_tokens NULL, output_tokens NULL, duration_ms, ok, at | idx (user_id, at) |
| `rate_limits` | key, window_start, count | PK (key, window_start) |
| `admin_audit` | id (autoincrement), admin_user_id, action, target, detail_json, at | idx at |

Foreign keys reference `users.id` / `cases.id` with `ON DELETE CASCADE` for case-owned
rows (messages, documents, signatures, memberships, invites, checklist, site builds,
jobs of the case) and `ON DELETE SET NULL` for history that must outlive a user
(`signatures.user_id`, `audit_log` actor strings stay as text). SQLite enables
`PRAGMA foreign_keys=ON` on every connection.

**Domain additions** (supersede the matching fields of ADR-0008 / ADR-0014):
`CaseRecord` gains `created_by: str | None = None` and `billing_user_id: str | None = None`;
`Signature` gains the evidence fields of ADR-0031.

### Engine and migrations (`persistence/engine.py`, T-005)

```python
def create_db_engine(url: str) -> Engine
    # sqlite: check_same_thread=False, foreign keys on, "sqlite://" uses StaticPool;
    # postgresql+psycopg: pool_pre_ping=True, statement_timeout 15 s
def init_db(engine: Engine) -> None        # alembic upgrade head, programmatically; idempotent
def schema_is_current(engine: Engine) -> bool   # readiness check (ADR-0034)
```

`alembic.ini` + `migrations/env.py` (T-001) read the URL from `load_settings().db_url`.
Production runs `alembic upgrade head` as a separate release step (compose service
`migrate`, ADR-0034); the app never migrates a production database on start. Dev and
tests call `init_db`.

**Rule for later schema changes:** a new file `migrations/versions/NNNN_<slug>.py` plus
the matching `tables.py` change, made by **at most one ticket per wave**, named in that
ticket's Owns by the Supervisor. v1 needs no change after 0001.

### Repositories (signatures stubbed by T-001; one owner each)

The case `Repository` (T-005) keeps every ADR-0012 method, with these changes:
`create_case(self, *, created_by: str | None = None, facts=None, state=None) -> CaseRecord`
(sets `billing_user_id = created_by`), `list_cases(self, case_ids: Sequence[str]) -> list[CaseRecord]`
(newest first; callers pass the user's member case ids), `set_billing_user(case_id, user_id)`,
`delete_case(case_id)` (cascades), `save_document` also stores signature evidence.

```python
class AccountsRepository:          # persistence/accounts.py, T-026
    def create_user(self, *, email, full_name, password_hash) -> User          # ConflictError on duplicate email
    def get_user(self, user_id) -> User; def find_user_by_email(self, email) -> User | None
    def get_password_hash(self, user_id) -> str; def set_password_hash(self, user_id, h) -> None
    def update_user(self, user_id, **fields) -> User; def delete_user(self, user_id) -> None
    def create_session(self, *, token_hash, user_id, expires_at, ip, user_agent) -> None
    def get_session(self, token_hash) -> SessionRecord | None
    def touch_session(self, token_hash, *, now, expires_at) -> None
    def revoke_session(self, token_hash) -> None
    def revoke_user_sessions(self, user_id, *, except_hash: str | None = None) -> int
    def create_token(self, *, token_hash, user_id, purpose, expires_at) -> None
    def use_token(self, token_hash, purpose, *, now) -> str          # returns user_id; TokenInvalidError
    def list_users(self, *, query: str | None, offset: int, limit: int) -> list[User]   # admin
class TeamRepository:              # persistence/team.py, T-027
    def add_member(self, m: Membership) -> Membership; def get_membership(self, case_id, user_id) -> Membership | None
    def list_members(self, case_id) -> list[Membership]; def member_case_ids(self, user_id) -> list[str]
    def update_member(self, case_id, user_id, **fields) -> Membership; def remove_member(self, case_id, user_id) -> None
    def create_invite(self, invite: Invite, *, token_hash: str) -> Invite
    def find_invite_by_token(self, token_hash) -> Invite | None; def list_invites(self, case_id) -> list[Invite]
    def mark_invite(self, invite_id, *, accepted_at=None, revoked_at=None) -> Invite
```

`EmailOutboxRepository` (T-028), `BillingRepository` (T-029), `JobsRepository` (T-030),
`LimitsRepository` (T-032), `PrivacyQueries` (T-037) and `AdminQueries` (T-038) are
specified in their ADRs (ADR-0029, ADR-0030, ADR-0028, ADR-0033, ADR-0034). All take an
`Engine` in their constructor and work on SQLite and PostgreSQL.

### Tests

T-005 proves the migration matches `tables.py` (Alembic autogenerate diff is empty) on
SQLite and, when `LAUNCH_TEST_POSTGRES_URL` is set, on PostgreSQL; upgrade -> downgrade
-> upgrade works. Repository tests run on a real SQLite file; CI also runs them on
PostgreSQL (ADR-0034).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Whole schema + first migration in wave 0, one migration slot per wave later (chosen) | No revision-chain collisions between 20 parallel tickets | Wave 0 must get the schema right |
| B. Each ticket adds its own migration | Local ownership | Parallel branches create divergent Alembic heads |
| C. `create_all` everywhere, migrations later | Simple now | Production data without migration history; the brief requires migrations |
| D. Postgres everywhere, also in tests | One dialect | Every builder needs a running Postgres; slower tests |

## Consequences

- Portable column types only (no JSONB, no arrays) so SQLite and PostgreSQL behave alike.
- The readiness endpoint can tell whether the database is at the latest migration.
- Deleting a company or user is a single cascading delete (ADR-0034 privacy rules).
