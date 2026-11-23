# T-005: Persistence: SQLite schema and Repository

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0012](../docs/adr/0012-persistence-and-data-model.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0007](../docs/adr/0007-stack-and-module-layout.md) |
| **Status** | todo |

## Goal

Cases, the full chat history, documents with versions and signatures, the audit log,
checklist progress and website builds are saved in SQLite and read back as domain
objects, so the product remembers everything across turns and restarts.

## Owns (only these paths may change)

- `launch_agents/persistence/`
- `tests/test_persistence.py`
- `evidence/T-005/`
- `prs/T-005.md`

## Contracts

- **Provides:** `create_db_engine(url)`, `init_db(engine)`, `Repository` with every method of ADR-0012 including `transaction()`.
- **Consumes:** domain types (T-001): `CaseRecord`, `CaseFacts`, `CaseState`, `ChatMessage`, `Document`, `Signature`, `AuditEntry`, `SiteBuild`, `NotFoundError`, `StaleVersionError`.

## Acceptance criteria

1. Tables, columns and constraints match ADR-0012; `init_db` is idempotent.
2. A case with two founders, `Decimal` equity and a non-default `CaseState` round-trips exactly (including dates and enum values).
3. `append_messages` assigns consecutive `seq` per case starting at 1, ids and timestamps; `list_messages(after_seq=n)` returns only later messages; two cases never share a sequence.
4. `save_document`: insert; update with the right `expected_version`; wrong `expected_version` raises `StaleVersionError`; a new version writes a `document_versions` row; only current-version signatures are returned.
5. `append_audit` / `list_audit` keep insertion order and filter by document; `delete_document` removes the document, its versions and signatures but keeps its audit entries.
6. Checklist ticks upsert; `get_checklist` returns `{item_id: done}`.
7. Site builds round-trip including the bundle files and QA reports; `latest_site_build` returns the highest version.
8. `transaction()` rolls everything back when the block raises.
9. Unknown ids raise `NotFoundError`; data survives a new `Repository` on the same file (restart test).
10. ORM objects never escape the package (public methods return pydantic models only).

## Feature run (`evidence/T-005/feature_run.py`)

Creates a temp SQLite file, stores a case, three chat messages (founder, Manager, Law
Agent handover), a document at v1 with one signature, then v2 (stale save attempted and
rejected), audit entries, two checklist ticks and a site build; then opens a **new**
engine on the same file and prints everything read back, asserting equality.

## Out of scope

Business rules (sign-off logic T-004, services T-013–T-015). No migrations tool.
