# ADR-0031: Electronic signatures and signed PDF / Word downloads

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor, product owner |
| **Tickets** | T-001 (types, constants, hash helper), T-004 (machine), T-031 (PDF/DOCX), T-015 (service), T-017 (routes), T-020 (screens) |
| **Scope** | `domain/documents.py` (Signature), `domain/constants.py`, `domain/helpers.py`, `signoff/`, `launch_agents/pdf/` |

## Context

ADR-0014 defined version-bound sign-off with "a signature is a recorded approval by the
founder picked in the switcher". The brief now requires a signature that holds up:
typed full name, an explicit consent checkbox, and a record of timestamp, signer
account, IP address and a hash of the exact document version; an executed document
downloads as a PDF with a signature page. External e-signature providers are a later
option. This ADR **supersedes ADR-0014's `Signature` type, the `sign`/`edit` signatures
and its "no real e-signature" rule**. Its document set, the state-machine rules (stale,
not-a-signer, already-signed, invalidation on edit, regenerate, executed, legal complete)
and the confirmed answers to Q-001 and Q-003 stay in force.

## Decision

### Types and constants (T-001)

```python
ESIGN_CONSENT_VERSION = "2026-11-23"
ESIGN_CONSENT_TEXT = ("I agree to sign this document electronically. I understand my typed name is my "
                      "signature and has the same effect as a handwritten signature, and that a record of "
                      "this signature (time, account, IP address and a fingerprint of the document) is kept.")
def document_sha256(content: str) -> str     # helpers.py: SHA-256 hex of UTF-8 content with \r\n -> \n
def names_match(typed: str, expected: str) -> bool   # case-insensitive, collapses whitespace, ignores . and ,

class SignatureEvidence(BaseModel):          # what the signer gives + what the server observed
    user_id: str | None                      # None only for system-seeded fixtures in tests
    typed_name: str
    consent_version: str
    content_sha256: str                      # of the version being signed (for an edit: of the new content)
    ip: str | None = None; user_agent: str | None = None
    acted_by_user_id: str | None = None      # demo mode only (ADR-0026)

class Signature(BaseModel):                  # replaces the ADR-0014 shape
    founder_id: str; version: int; signed_at: datetime
    user_id: str | None; typed_name: str; consent_version: str; content_sha256: str
    ip: str | None = None; user_agent: str | None = None; acted_by_user_id: str | None = None
```

`AuditAction` gains `PDF_DOWNLOADED = "pdf_downloaded"`, `MEMBER_JOINED = "member_joined"`,
`INVITE_SENT = "invite_sent"` and `PLAN_CHANGED = "plan_changed"`.

### State machine (T-004, changes to ADR-0014)

```python
def sign(doc: Document, founder_id: str, version: int, *, evidence: SignatureEvidence, now: datetime) -> SignOffOutcome
def edit(doc: Document, editor_id: str, version: int, new_content: str, *,
         evidence: SignatureEvidence, now: datetime) -> SignOffOutcome
```

Rule 1 is extended: `evidence.content_sha256` must equal `document_sha256(doc.content)`
for `sign` (and `document_sha256(new_content)` for `edit`), else `REJECTED_STALE` with
`StaleVersionError` ("This document changed while you were reviewing it..."). For an edit
the editor signs the **new** version with their own evidence (replacing ADR-0014's
"signature carried over"), so every recorded signature was given to exactly the content
it names. `create_document` and `regenerate` are unchanged.

### Service rules (T-015)

`LegalService.sign(access, document_id, SignRequest)` with
`SignRequest{version, content_sha256, typed_name, consent: Literal[True]}`:

1. `access.require(Permission.SIGN)`, `access.require_feature(Feature.ESIGN)`; the user's
   email must be verified (`EmailNotVerifiedError`).
2. The signing founder is `access.founder_id` (never a body field).
3. `typed_name` must match that founder's name in the facts (`names_match`), else
   `InvalidStateError` ("Type your full name as it appears in the documents: Alice Chen").
4. `consent` must be true; the evidence records `ESIGN_CONSENT_VERSION`.
5. Evidence is built by the service from the access (user id, IP, user agent,
   `acted_by_user_id`) plus the body, and passed to the machine.

`edit` takes the same fields plus `content`. The audit `SIGNED` / `EDITED` entries carry
`detail = {"user_id", "typed_name", "content_sha256", "ip"}`.

### Downloads (`pdf/`, T-031; served by T-017)

```python
class SignerInfo(BaseModel): full_name: str; email: str | None = None     # per founder id
def render_signed_pdf(doc: Document, *, company_name: str, signers: Mapping[str, SignerInfo],
                      audit: Sequence[AuditEntry], generated_at: datetime) -> bytes
def render_docx(doc: Document, *, company_name: str) -> bytes
def markdown_blocks(content: str) -> list[Block]     # the small Markdown subset the Law Agent writes
```

- **Signed PDF** (executed documents only, else `NotExecutedError`): page header with
  company, title, "Version {n} - Executed {date}"; the document body rendered from its
  Markdown (headings, paragraphs, bold/italic, bullet and numbered lists); a
  **signature page** with one block per signer (typed name in italics, the
  founder's full name, the signer's account email, signed at UTC, IP address, consent
  version, and "acted in demo mode" when `acted_by_user_id` is set) and
  the document's SHA-256; a **certificate of completion** listing this document's audit
  entries; every page footer carries "Document {id} - v{n} - SHA-256 {first 16 hex} -
  page x of y" and the `LEGAL_NOTICE`. reportlab with `invariant=1`, so the same inputs
  produce the same bytes (tests compare hashes). Placeholders such as `[ADDRESS]` stay
  as they are: the app never stores SSNs, tax ids or home addresses (ADR-0033).
- **Word copy** (`.docx`, any status, gated by `SIGNED_PDF`): the same body with the
  placeholders highlighted, so founders fill them in **in the downloaded file only**.
  The first page says "Editable copy - not the signed record".
- Each download is audited (`PDF_DOWNLOADED`, detail `{"format"}`).

Legal footing (shown in the signing dialog and the Terms): signatures are made under the
US ESIGN Act and UETA with the consent above; the product is not a law firm.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Built-in e-signature with evidence bound to a content hash + signed PDF (chosen) | Meets the brief; verifiable record; no vendor | Not a certified e-signature platform |
| B. DocuSign / Dropbox Sign | Recognised brand | Cost, integration, out of scope for v1 (brief) |
| C. Click-to-approve only (ADR-0014) | Simplest | No consent, no evidence; not a signature |

## Consequences

- A signature can always be traced to one account, one moment and one exact text.
- Editing a document asks the editor to sign the new version in the same dialog.
- Moving to an external provider later replaces `sign` behind the same service call.
