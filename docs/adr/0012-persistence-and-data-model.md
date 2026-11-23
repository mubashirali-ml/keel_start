# ADR-0012: Persistence and data model (SQLite via SQLAlchemy)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-005 (implements), T-013, T-014, T-015, T-016 (consume) |
| **Scope** | `launch_agents/persistence/` |

## Context

The Manager must remember the case across many chat turns; documents have versions,
signatures and an audit log; checklist progress must be saved; site builds keep their QA
reports and deploy state. The brief fixes SQLite. Services (wave 2) need one repository
API, defined before they are built.

## Decision

SQLAlchemy 2.0 with declarative tables in `persistence/tables.py`. Pydantic domain
objects are the only thing crossing the repository boundary; ORM rows never leave
`persistence/`. Nested domain objects are stored as JSON text (`model_dump_json`).

### Tables

| Table | Columns (type) | Keys / constraints |
|---|---|---|
| `cases` | `id` TEXT, `created_at` DATETIME, `updated_at` DATETIME, `facts_json` TEXT, `state_json` TEXT | PK `id` |
| `messages` | `id` TEXT, `case_id` TEXT, `seq` INT, `role` TEXT, `agent` TEXT NULL, `founder_id` TEXT NULL, `kind` TEXT, `content` TEXT, `payload_json` TEXT, `suggested_json` TEXT, `created_at` DATETIME | PK `id`; FK `case_id`; UNIQUE(`case_id`,`seq`) |
| `documents` | `id` TEXT, `case_id` TEXT, `kind` TEXT, `founder_id` TEXT NULL, `title` TEXT, `version` INT, `content` TEXT, `status` TEXT, `required_signers_json` TEXT, `created_at`, `updated_at` | PK `id`; UNIQUE(`case_id`,`kind`,`founder_id`) |
| `document_versions` | `document_id` TEXT, `version` INT, `content` TEXT, `created_by` TEXT, `created_at` | PK(`document_id`,`version`) |
| `signatures` | `document_id` TEXT, `founder_id` TEXT, `version` INT, `signed_at` | PK(`document_id`,`founder_id`,`version`) |
| `audit_log` | `id` INTEGER autoincrement, `case_id` TEXT, `document_id` TEXT NULL, `actor` TEXT, `action` TEXT, `from_version` INT NULL, `to_version` INT NULL, `detail_json` TEXT, `at` DATETIME | PK `id`; index (`case_id`,`id`) |
| `checklist_items` | `case_id` TEXT, `item_id` TEXT, `done` BOOL, `updated_by` TEXT NULL, `updated_at` | PK(`case_id`,`item_id`) |
| `site_builds` | `id` TEXT, `case_id` TEXT, `version` INT, `content_json` TEXT, `files_json` TEXT, `qa_reports_json` TEXT, `qa_passed` BOOL, `fix_rounds` INT, `status` TEXT, `deploy_url` TEXT NULL, `deploy_message` TEXT NULL, `override_by` TEXT NULL, `created_at`, `updated_at` | PK `id`; UNIQUE(`case_id`,`version`) |

The cap table is not stored: it is computed from the case facts on demand (ADR-0013),
which is what keeps documents and the cap table consistent. Only signatures for the
current document version count; older rows stay for history.

### Repository (`persistence/repository.py`)

```python
def create_db_engine(url: str) -> Engine            # sqlite: check_same_thread=False; "sqlite://" uses StaticPool
def init_db(engine: Engine) -> None                 # create_all; idempotent

class Repository:
    def __init__(self, engine: Engine) -> None
    # cases
    def create_case(self, facts: CaseFacts | None = None, state: CaseState | None = None) -> CaseRecord
    def get_case(self, case_id: str) -> CaseRecord                    # NotFoundError
    def list_cases(self) -> list[CaseRecord]                          # newest first
    def save_case(self, case: CaseRecord) -> CaseRecord               # bumps updated_at
    # messages
    def append_messages(self, case_id: str, messages: Sequence[ChatMessage]) -> list[ChatMessage]
        # assigns id, case_id, seq (max+1...), created_at; returns stored copies in order
    def list_messages(self, case_id: str, after_seq: int | None = None, limit: int | None = None) -> list[ChatMessage]
    # documents + sign-off
    def save_document(self, doc: Document, *, expected_version: int | None, created_by: str) -> Document
        # insert when new; else optimistic check: stored version must equal expected_version
        # (else StaleVersionError); writes document_versions row when version is new;
        # replaces signatures for doc.version with doc.signatures
    def get_document(self, document_id: str) -> Document              # NotFoundError
    def list_documents(self, case_id: str) -> list[Document]          # stable order: kind, founder order
    def delete_document(self, document_id: str) -> None               # removes doc + its versions/signatures (audit stays)
    def append_audit(self, entries: Sequence[AuditEntry]) -> list[AuditEntry]
    def list_audit(self, case_id: str, document_id: str | None = None) -> list[AuditEntry]   # oldest first
    # checklist
    def set_checklist_item(self, case_id: str, item_id: str, done: bool, updated_by: str | None) -> None
    def get_checklist(self, case_id: str) -> dict[str, bool]
    # site builds
    def save_site_build(self, build: SiteBuild) -> SiteBuild          # insert or update by id
    def get_site_build(self, build_id: str) -> SiteBuild
    def latest_site_build(self, case_id: str) -> SiteBuild | None
    def list_site_builds(self, case_id: str) -> list[SiteBuild]
```

Every method runs in its own transaction (`Session.begin()`). Services that need several
writes to be atomic call `repo.transaction()` (a context manager yielding the same
repository bound to one session) — T-005 provides it:

```python
    @contextmanager
    def transaction(self) -> Iterator["Repository"]: ...
```

### Database location

`Settings.db_url`, default `sqlite:///./launch_agents.db` (git-ignored by `*.db`). Tests
and recorded runs use a temp-dir file URL or `sqlite://`. No migrations tool in the first
release: `init_db` creates tables; a schema change is a new ADR and, if needed, a
recreate-on-mismatch rule.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. SQLAlchemy tables + pydantic at the boundary, JSON columns for nested state (chosen) | Simple; queryable where it matters (messages, docs, audit) | JSON columns are not queryable |
| B. Fully normalised founders/facts tables | Queryable | Lots of joins for data only read as a whole |
| C. LangGraph SQLite checkpointer for case memory | Built in | Opaque to the API; tied to library internals |

## Consequences

- Optimistic version checks in `save_document` back up the sign-off state machine against
  concurrent edits (two founders acting at once).
- Repository tests run against a real SQLite file, not mocks.
