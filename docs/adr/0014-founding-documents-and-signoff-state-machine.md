# ADR-0014: Founding documents and the multi-party sign-off state machine

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (types), T-004 (state machine), T-006 (drafting), T-015 (service), T-017 (API), T-020 (UI) |
| **Scope** | `launch_agents/domain/documents.py`, `launch_agents/signoff/`, `launch_agents/agents/law/documents.py` |

## Context

The Law Agent drafts a Founder IP Assignment Agreement, a Bylaws Summary (Operating
Agreement Summary for an LLC) and an IRS 83(b) election per founder. Each document has a
version; it becomes Executed when every required founder has signed the current version;
an edit raises the version and cancels other founders' signatures (the editor's
signature moves to the new version); stale actions are rejected; everything is audited.
There is no real authentication or e-signature in the first release: a "signature" is a
recorded approval by the founder selected in the founder switcher.

## Decision

### Types (`domain/documents.py`)

```python
class DocumentKind(str, Enum):
    IP_ASSIGNMENT = "ip_assignment"; BYLAWS_SUMMARY = "bylaws_summary"
    OPERATING_AGREEMENT_SUMMARY = "operating_agreement_summary"; ELECTION_83B = "election_83b"
class DocumentStatus(str, Enum): AWAITING_SIGNATURES = "awaiting_signatures"; EXECUTED = "executed"
class Signature(BaseModel): founder_id: str; version: int; signed_at: datetime
class DraftDocument(BaseModel):
    kind: DocumentKind; title: str; founder_id: str | None; content: str; required_signers: list[str]
class Document(BaseModel):
    id: str; case_id: str; kind: DocumentKind; title: str; founder_id: str | None
    version: int; content: str; status: DocumentStatus; required_signers: list[str]
    signatures: list[Signature]          # current version only
    created_at: datetime; updated_at: datetime
class AuditAction(str, Enum):
    CREATED = "created"; SIGNED = "signed"; EDITED = "edited"
    SIGNATURES_INVALIDATED = "signatures_invalidated"; EXECUTED = "executed"; REOPENED = "reopened"
    REGENERATED = "regenerated"; REJECTED_STALE = "rejected_stale"
    REJECTED_NOT_SIGNER = "rejected_not_signer"; REJECTED_ALREADY_SIGNED = "rejected_already_signed"
    LEGAL_COMPLETE = "legal_complete"
    FACTS_LOCKED = "facts_locked"; NAME_CHOSEN = "name_chosen"; CHECKLIST_UPDATED = "checklist_updated"
    SITE_BUILT = "site_built"; SITE_DEPLOYED = "site_deployed"; DEPLOY_OVERRIDE = "deploy_override"
class AuditEntry(BaseModel):
    id: int | None = None; case_id: str; document_id: str | None = None
    actor: str                          # founder id, "system", or an AgentId value
    action: AuditAction; from_version: int | None = None; to_version: int | None = None
    detail: dict[str, Any] = {}; at: datetime
```

### Which documents, who signs

| Entity | Documents (in this order) | Required signers |
|---|---|---|
| Delaware C-Corp | Founder IP Assignment Agreement; Bylaws Summary; IRS 83(b) Election — {founder} (one per founder) | IP + Bylaws: all founders. 83(b): **that founder only** (default, open question Q-001) |
| LLC | Founder IP Assignment Agreement; Operating Agreement Summary; IRS 83(b) Election — {founder} | same |

Drafting (`agents/law/documents.py`, T-006):
`draft_documents(facts: CaseFacts, cap_table: CapTable, today: date) -> list[DraftDocument]`.
Content is Markdown. It starts and ends with `LEGAL_NOTICE`, quotes share/unit counts
**only** from `cap_table.rows`, uses the company name (or `[COMPANY NAME]`), and leaves
unknown details as bracketed placeholders: `[ADDRESS]`, `[TAXPAYER ID]`,
`[FAIR MARKET VALUE PER SHARE]`, `[REGISTERED AGENT]`, `[SPOUSE NAME, IF ANY]`. The 83(b)
form states the transfer date (incorporation date), the deadline (`deadline_83b`) and the
number of shares/units and vesting terms of that founder.

### State machine (`signoff/machine.py`, T-004, pure functions, no I/O)

```
            create()                    sign() by last missing signer
  (none) ───────────────> AWAITING ────────────────────────────────> EXECUTED
                          v1..vN   <──────── edit() / regenerate() ────┘  (REOPENED)
                            │ └──── edit(): version+1, others' signatures cancelled,
                            │       editor's signature carried to the new version
                            └──── sign()/edit() with version != current -> rejected (stale)
```

```python
class SignOffOutcome(BaseModel):
    ok: bool
    document: Document                  # unchanged when ok is False
    audit: list[AuditEntry]             # ALWAYS returned, also for rejections -> persist it
    invalidated: list[str] = []         # founder ids whose signatures were cancelled
    error: LaunchError | None = None    # StaleVersionError | NotASignerError | AlreadySignedError
    model_config = ConfigDict(arbitrary_types_allowed=True)

def create_document(case_id: str, draft: DraftDocument, *, now: datetime) -> SignOffOutcome
def sign(doc: Document, founder_id: str, version: int, *, now: datetime) -> SignOffOutcome
def edit(doc: Document, editor_id: str, version: int, new_content: str, *, now: datetime) -> SignOffOutcome
def regenerate(doc: Document, draft: DraftDocument, *, now: datetime, actor: str = "system") -> SignOffOutcome
def is_legal_complete(docs: Sequence[Document]) -> bool    # non-empty and all EXECUTED
```

Rules, checked in this order:

1. `version != doc.version` -> `REJECTED_STALE` audit, `StaleVersionError` ("This document
   changed to version {n} while you were looking at it. Review the new version first.").
2. `sign`: founder not in `required_signers` -> `REJECTED_NOT_SIGNER`, `NotASignerError`.
   Already signed this version -> `REJECTED_ALREADY_SIGNED`, `AlreadySignedError`.
   Otherwise add the signature (`SIGNED`); if every required signer has signed ->
   status `EXECUTED` and an `EXECUTED` entry.
3. `edit`: editor must be a required signer (else `REJECTED_NOT_SIGNER`). Content
   unchanged -> no-op, `ok=True`, no audit. Otherwise `version += 1`, signatures of
   everyone except the editor are cancelled (`SIGNATURES_INVALIDATED` with
   `detail={"founders": [...]}`), the editor's signature is recorded on the new version,
   `EDITED` from_version/to_version. If the document was `EXECUTED` it gets `REOPENED`
   first (default, open question Q-003). If the editor is the only required signer the
   document is executed again immediately.
4. `regenerate` (facts changed after drafting, e.g. new equity split): if content differs,
   `version += 1`, **all** signatures cancelled, `REGENERATED` (+ `REOPENED` if it was
   executed); identical content is a no-op.

`LegalService` (T-015) persists `outcome.audit` even when `ok` is False, then raises
`outcome.error`; it writes `LEGAL_COMPLETE` the first time `is_legal_complete` turns true.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Pure state machine returning outcome + audit, persisted by the service (chosen) | Fully unit-testable; rejections audited too | Service must remember to persist audit on failure |
| B. State machine inside the repository | Atomic by construction | Logic tied to SQL; hard to test |
| C. Real e-signature provider | Legally meaningful | Out of scope for the first release (brief) |

## Consequences

- "Signature" means "approved in the app as founder X"; the UI and documents say so
  (no real authentication or e-signature in the first release).
- Stale-version protection exists twice: in the machine (version argument) and in
  `Repository.save_document(expected_version=...)` for concurrent writes.
