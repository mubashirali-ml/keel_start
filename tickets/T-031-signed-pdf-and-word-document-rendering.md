# T-031: Signed PDF and editable Word rendering of founding documents

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0041](../docs/adr/0041-brand-keelstart-everywhere-customers-look.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0033](../docs/adr/0033-security-hardening.md) |
| **Status** | todo |

## Goal

An executed founding document downloads as a professional PDF with a signature page that
records who signed, when, from which IP and against which exact text, plus a certificate
of completion; and any document downloads as an editable Word copy where founders fill in
the placeholders themselves.

## Owns (only these paths may change)

- `launch_agents/pdf/`
- `tests/test_pdf.py`
- `evidence/T-031/`
- `prs/T-031.md`

## Contracts

- **Provides:** `SignerInfo`, `render_signed_pdf(doc, *, company_name, signers, audit, generated_at, brand_name=BRAND_NAME) -> bytes`, `render_docx(doc, *, company_name, brand_name=BRAND_NAME) -> bytes`, `markdown_blocks(content) -> list[Block]` (ADR-0031).
- **Consumes:** `Document`, `Signature`, `AuditEntry`, `DocumentStatus`, `NotExecutedError`, `LEGAL_NOTICE`, `document_sha256` (T-001); packages `reportlab`, `python-docx`.

## Acceptance criteria

1. `markdown_blocks` parses the Law Agent's Markdown subset (headings 1–3, paragraphs, `**bold**`, `*italic*`, bullet and numbered lists, horizontal rules) and treats everything else as plain text (no HTML, no images, no links fetched).
2. `render_signed_pdf` on a non-executed document -> `NotExecutedError` ("This document can be downloaded as a signed PDF once every founder has signed it.").
3. The PDF contains (asserted on the flowables the renderer builds and, rendered with page compression off, on the PDF content streams): company, title, "Version n", the full body, one signature block per signer with typed name, founder name, account email, UTC timestamp, IP, consent version, the document SHA-256, "acted in demo mode" when applicable, the certificate of completion with this document's audit entries, and on every page the footer with document id, version, hash prefix, page x of y and `LEGAL_NOTICE`.
4. Placeholders (`[ADDRESS]`, `[TAXPAYER ID]` ...) are kept verbatim; no other personal data is added.
5. Determinism: same inputs -> byte-identical PDF (`invariant=1`), asserted by hashing two renders.
6. `render_docx` returns a valid `.docx` (opens with python-docx) with the title, the ADR-0041 editable-copy note, the body, and every placeholder highlighted; works for any status.
7. Non-ASCII names (e.g. "José Núñez") render correctly using the Vera TrueType fonts bundled with reportlab (embedded; italic for the typed signature); no font files are downloaded.
8. A 30-page document renders in under 2 s.
9. Branding (ADR-0041): PDF metadata creator and producer are the brand name, title is the document title and author the company; the certificate is titled "Certificate of completion - Keelstart e-signature record"; every page footer ends with "Signed with Keelstart"; the Word copy's core properties creator is the brand and its first-page note reads "Editable copy from Keelstart - not the signed record"; passing `brand_name="Acme Sign"` changes all of them; the document body never names the brand. Tests compare against `BRAND_NAME` / `settings.brand_name` or pass the brand explicitly, never a typed-out default, so they pass before and after T-047 changes the default to "Keelstart" (ADR-0041).

## Feature run (`evidence/T-031/feature_run.py`)

Builds an executed IP Assignment for Alice and Bob with two signatures (evidence) and its
audit trail, renders the signed PDF twice and prints both SHA-256 hashes (equal), the
page count and the extracted signature-page text; renders the Word copy and prints its
paragraph count and highlighted placeholders; shows the `NotExecutedError` for an
awaiting document. Writes both files to a temp dir and prints their paths and sizes.

## Out of scope

Serving downloads and access checks (T-015, T-017), the Legal screen (T-020).
