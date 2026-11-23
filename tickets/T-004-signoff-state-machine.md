# T-004: Multi-party sign-off state machine with audit entries

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0007](../docs/adr/0007-stack-and-module-layout.md) |
| **Status** | todo |

## Goal

Documents can be created, signed, edited and regenerated under the exact sign-off rules
(versions, invalidation, stale rejection, execution), with an audit entry for every
action including rejected ones.

## Owns (only these paths may change)

- `launch_agents/signoff/`
- `tests/test_signoff.py`
- `evidence/T-004/`
- `prs/T-004.md`

## Contracts

- **Provides:** `SignOffOutcome`, `create_document`, `sign`, `edit`, `regenerate`, `is_legal_complete` (ADR-0014), as pure functions with an injected `now`.
- **Consumes:** `Document`, `DraftDocument`, `Signature`, `AuditEntry`, `AuditAction`, `StaleVersionError`, `NotASignerError`, `AlreadySignedError`, `new_id` (T-001).

## Acceptance criteria

1. `create_document` returns version 1, `awaiting_signatures`, no signatures, one `created` entry.
2. Two-signer document: first `sign` -> still awaiting, one `signed` entry; second -> `executed` plus `executed` entry.
3. `edit` by founder A on a document signed by A and B: version 2, only A's signature (on v2), `invalidated == [B]`, entries `signatures_invalidated` (detail lists B) and `edited` (from 1 to 2), status awaiting.
4. `edit` of an executed document reopens it (`reopened` entry) and follows rule 3; single-signer 83(b) edited by its founder is executed again immediately.
5. Any `sign`/`edit` with `version != doc.version` returns `ok=False`, the unchanged document, a `rejected_stale` entry and a `StaleVersionError` whose message names the current version.
6. Signing by a non-signer -> `rejected_not_signer` + `NotASignerError`; signing twice -> `rejected_already_signed` + `AlreadySignedError`; editing with identical content -> no-op with no audit.
7. `regenerate` with new content cancels all signatures, bumps the version, `regenerated` entry (+ `reopened` if executed); identical content is a no-op.
8. `is_legal_complete` is False for an empty list, True only when all are executed.
9. Inputs are never mutated (tests compare before/after copies).

## Feature run (`evidence/T-004/feature_run.py`)

Walks one IP-assignment document for Alice and Bob through: create, Alice signs, Bob
edits (Alice's signature cancelled, Bob's moves to v2), Alice tries to sign v1 (stale,
rejected), Alice signs v2 (executed), then a regenerate reopening it. Prints the status,
version, signatures and the full audit list after each step, asserting each.

## Out of scope

Persistence (T-005, T-015), drafting the content (T-006), UI (T-020).
