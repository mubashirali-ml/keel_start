# T-015: Legal service: cap table, document generation, sign-off and audit trail

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-002, T-003, T-004, T-005, T-006 |
| **ADRs** | [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0012](../docs/adr/0012-persistence-and-data-model.md) |
| **Status** | todo |

## Goal

The product can produce the cap table and its downloads from the case, draft the
founding documents from the locked facts so share counts always match, and run
multi-founder sign-off with versions, invalidation, stale-version rejection and a
complete audit trail, marking the legal step complete when everything is executed.

## Owns (only these paths may change)

- `launch_agents/workflows/legal.py`
- `tests/test_legal_service.py`
- `evidence/T-015/`
- `prs/T-015.md`

## Contracts

- **Provides:** `LegalService(repo, llm, *, clock=utcnow)` implementing `LegalServicePort` (ADR-0017).
- **Consumes:** `validate_facts` (T-002), `build_cap_table`, `cap_table_csv`, `cap_table_xlsx` (T-003), `create_document`, `sign`, `edit`, `regenerate`, `is_legal_complete` (T-004), `Repository` (T-005), `draft_documents` (T-006).

## Acceptance criteria

1. `cap_table` validates the facts (defaults applied) and raises `FactsNotReadyError` with the first issue's friendly message when invalid; CSV/XLSX come from the same table.
2. `generate_documents` requires locked facts (`FactsNotReadyError` otherwise); first call creates every document (v1, `created` audit) and returns a Law Agent `documents_ready` message (payload count + view "legal") and a Cap Table Builder `cap_table_ready` message; share counts in every document equal the cap table.
3. A second `generate_documents` after a fact change (e.g. equity 60/40 -> 55/45) regenerates each changed document (new version, all signatures cancelled, `regenerated` audit), leaves unchanged ones alone, and creates/removes 83(b) documents when founders were added/removed (removal is audited).
4. `sign` and `edit` load the document, apply the T-004 machine, **persist the audit entries even when the action is rejected**, save with `expected_version` (concurrent stale write -> `StaleVersionError`), then raise the machine's error if any.
5. `edit` returns `EditOutcome` with the invalidated founder ids; executing the last document writes one `legal_complete` audit entry (only the first time); `legal_complete` reflects `is_legal_complete`.
6. `audit` returns every entry for the case, oldest first, including entries written by other services.
7. All writes for one action happen in one `repo.transaction()`.

## Feature run (`evidence/T-015/feature_run.py`)

With a temp SQLite repository and `FakeLLM`: stores the sample case with locked facts and
a company name; prints the cap table and the CSV; generates documents (prints titles,
versions, required signers); Alice signs all of hers; Bob edits the IP assignment (Alice's
signature cancelled, printed); Alice tries the old version (stale, rejected and audited);
everyone signs the current versions; prints `legal_complete` and the full audit trail;
finally changes the equity split, re-locks, regenerates, and shows the documents back to
awaiting signatures with new share counts.

## Out of scope

HTTP routes (T-017), Legal and Cap Table screens (T-020, T-021).
