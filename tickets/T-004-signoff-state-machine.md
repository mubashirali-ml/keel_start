# T-004: Multi-party sign-off state machine with e-signature evidence and audit entries

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md) |
| **Status** | merged |

## Goal

Documents can be created, signed, edited and regenerated under the exact sign-off rules
(versions, invalidation, stale rejection, execution), every signature is bound to the
exact content it was given to, and every action, including rejected ones, has an audit entry.

## Owns (only these paths may change)

- `launch_agents/signoff/`
- `tests/test_signoff.py`
- `evidence/T-004/`
- `prs/T-004.md`

## Contracts

- **Provides:** `SignOffOutcome`, `create_document`, `sign(doc, founder_id, version, *, evidence, now)`, `edit(doc, editor_id, version, new_content, *, evidence, now)`, `regenerate`, `is_legal_complete` (ADR-0014 rules with the ADR-0031 changes), pure functions with an injected `now`.
- **Consumes:** `Document`, `DraftDocument`, `Signature`, `SignatureEvidence`, `AuditEntry`, `AuditAction`, `document_sha256`, `StaleVersionError`, `NotASignerError`, `AlreadySignedError`, `new_id` (T-001).

## Acceptance criteria

1. `create_document` returns version 1, `awaiting_signatures`, no signatures, one `created` entry.
2. Two-signer document: first `sign` -> still awaiting, one `signed` entry whose detail has `user_id`, `typed_name`, `content_sha256`, `ip`; the stored `Signature` carries every evidence field; second -> `executed` plus `executed` entry.
3. `sign` whose `evidence.content_sha256` differs from `document_sha256(doc.content)` -> `ok=False`, `rejected_stale`, `StaleVersionError` (same as a wrong version number).
4. `edit` by founder A on a document signed by A and B: version 2, exactly one signature (A's, on v2, with the evidence given for the **new** content), `invalidated == [B]`, entries `signatures_invalidated` (detail lists B) and `edited` (from 1 to 2), status awaiting; an edit whose evidence hash does not match `new_content` is rejected as stale.
5. `edit` of an executed document reopens it (`reopened` entry) and follows rule 4; a single-signer 83(b) edited by its founder is executed again immediately.
6. Any `sign`/`edit` with `version != doc.version` returns `ok=False`, the unchanged document, a `rejected_stale` entry and a `StaleVersionError` whose message names the current version.
7. Non-signer -> `rejected_not_signer` + `NotASignerError`; signing twice -> `rejected_already_signed` + `AlreadySignedError`; editing with identical content -> no-op, no audit.
8. `regenerate` with new content cancels all signatures, bumps the version, `regenerated` entry (+ `reopened` if executed); identical content is a no-op.
9. `is_legal_complete` is False for an empty list, True only when all are executed; inputs are never mutated.

## Feature run (`evidence/T-004/feature_run.py`)

Walks one IP-assignment document for Alice and Bob: create; Alice signs with evidence
(typed name, consent version, hash, IP); Bob edits (Alice's signature cancelled, Bob's
new evidence on v2); Alice tries v1 (stale, rejected); Alice tries v2 with the v1 hash
(stale, rejected); Alice signs v2 (executed); a regenerate reopens it. Prints status,
version, signatures with evidence and the audit list after each step, asserting each.

## Out of scope

Persistence and name/consent/verification checks (T-015), PDFs (T-031), drafting (T-006), UI (T-020).
