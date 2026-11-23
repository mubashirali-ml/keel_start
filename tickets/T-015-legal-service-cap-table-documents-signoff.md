# T-015: Legal service: cap table, document generation, electronic signatures, signed downloads and audit trail

| | |
|---|---|
| **Wave** | 2 |
| **Depends on** | T-001, T-002, T-003, T-004, T-005, T-006, T-026, T-027, T-031 |
| **ADRs** | [ADR-0039](../docs/adr/0039-brand-charterly-everywhere-customers-look.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) |
| **Status** | todo |

## Goal

The product produces the cap table and its downloads, drafts the founding documents from
the locked facts so share counts always match, and runs multi-founder electronic signing
(typed name, consent, verified email, bound to the exact text) with versions,
invalidation, stale rejection, notifications and a complete audit trail; executed
documents download as signed PDFs, and every document as an editable Word copy.

## Owns (only these paths may change)

- `launch_agents/workflows/legal.py`
- `tests/test_legal_service.py`
- `evidence/T-015/`
- `prs/T-015.md`

## Contracts

- **Provides:** `LegalService(repo, accounts, team, notifier, *, clock=utcnow)` implementing `LegalServicePort` (ADR-0032), including `regenerate_if_drafted`, `get_document`, `signed_pdf`, `docx`.
- **Consumes:** `validate_facts` (T-002), `build_cap_table`, `cap_table_csv`, `cap_table_xlsx` (T-003), the T-004 machine with `SignatureEvidence`, `Repository` (T-005), `draft_documents` (T-006), `TeamRepository` (T-027) for signer accounts, `AccountsRepository` (T-026; tests may use an in-file fake for email-verified lookups), `render_signed_pdf`, `render_docx` (called with `brand_name=settings.brand_name`, ADR-0039), `SignerInfo` (T-031), `Notifier`/`RecordingNotifier`, `CaseAccess`, `SignRequest`, `EditRequest`, `names_match`, `ESIGN_CONSENT_VERSION` (T-001).

## Acceptance criteria

1. Cap table and CSV/XLSX as before (validated facts, `FactsNotReadyError` with the first friendly issue); available on every plan.
2. `generate_documents` needs `EDIT_DOCUMENTS` and `Feature.DOCUMENTS` (Free -> `PlanRequiredError` "Drafting founding documents is included in the Launch and Team plans.", details `required_plan: "launch"` (ADR-0038)), locked facts, creates every document with the Law Agent `documents_ready` and Cap Table Builder `cap_table_ready` messages, share counts equal the cap table, and calls `notifier.signatures_needed` for each document's signers.
3. `regenerate_if_drafted` after a fact change regenerates changed documents (all signatures cancelled, `regenerated` audit), adds/removes 83(b)s, notifies the affected signers; no documents -> no-op.
4. `sign(access, id, SignRequest)`: `SIGN` + `ESIGN`; unverified email -> `EmailNotVerifiedError`; the founder is `access.founder_id` (never from the body); typed name must match the founder's name (`InvalidStateError` naming the expected name); `consent` must be true; the client hash must equal the current content hash (else stale); the evidence carries user id, IP, user agent, consent version, `acted_by_user_id`; audit entries persisted **even when rejected**; saved with `expected_version`; then raises the machine's error if any.
5. `edit(access, id, EditRequest)`: `EDIT_DOCUMENTS` + `ESIGN`; the editor e-signs the new content; returns `EditOutcome` with invalidated founder ids; `notifier.signatures_needed` for the invalidated founders; the first time everything is executed, one `legal_complete` audit entry; each newly executed document triggers `notifier.document_executed`.
6. `signed_pdf` (`SIGNED_PDF` feature; executed only, else `NotExecutedError`) and `docx` return `(filename, bytes)` with names like `crumb-ledger-ip-assignment-v2-signed.pdf`, use signer names/emails from the team and the document's audit entries, and audit `pdf_downloaded`.
7. A document id from another company -> `NotFoundError`; all writes for one action in one `repo.transaction()`; `audit` returns every entry oldest first.

## Feature run (`evidence/T-015/feature_run.py`)

Temp SQLite repository, team with Alice (f1, verified) and Bob (f2, verified),
`RecordingNotifier`, Launch entitlements: prints the cap table and CSV; generates
documents (titles, versions, signers, notifications); Alice signs all hers (prints the
evidence); Bob edits the IP assignment (Alice invalidated, notification printed); Alice
tries the old version and a wrong typed name (both rejected and audited); everyone signs;
prints `legal_complete`, the audit trail, and the signed PDF's size and hash; shows the
Free-plan refusal and the unverified-email refusal; changes the equity split, re-locks,
regenerates and shows the documents back to awaiting signatures with new share counts.

## Out of scope

HTTP routes (T-017), Legal and Cap Table screens (T-020, T-021), sending the emails (T-035).
