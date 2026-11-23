# T-017: HTTP API: cap table, documents and e-signatures, signed downloads, audit, and website jobs

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-005, T-013, T-015, T-027, T-031, T-032 |
| **ADRs** | [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md) |
| **Status** | todo |

## Goal

Over HTTP, members of a company can view and download the cap table, generate, e-sign
and edit the founding documents (with stale-version protection), download signed PDFs
and editable Word copies, read the audit trail, and start, follow, preview, download and
publish website builds, each request authorized for that company and plan.

## Owns (only these paths may change)

- `launch_agents/api/routes/legal.py`
- `launch_agents/api/routes/website.py`
- `tests/test_api_legal.py`
- `tests/test_api_website.py`
- `evidence/T-017/`
- `prs/T-017.md`

## Contracts

- **Provides:** the T-017 rows of the ADR-0032 endpoint table as `router = APIRouter()` in each file, request bodies in the same files (`extra="forbid"`, ADR-0033 limits).
- **Consumes:** `require_case`, `rate_limit`, `get_services` (T-016 `api/deps.py`, same wave: tests build a minimal app with the T-001 error handlers and their own `require_case` override built on `authorize_case` from T-027), `LegalService` (T-015), `WebsiteService` (T-013), domain views and errors (T-001).

## Acceptance criteria

1. Every route uses `require_case(<permission from ADR-0032>)`; an unauthenticated call -> 401; a non-member -> 404 (same body as an unknown company); a member without the permission -> 403.
2. Cap table JSON and `.csv`/`.xlsx` downloads with `Content-Disposition: attachment; filename="<company-slug>-cap-table.<ext>"`; invalid facts -> 409 `facts_not_ready`.
3. Documents: generate (409 not locked; 402 `plan_required` on Free), list, get, sign (`SignRequest` with typed name, consent, hash, version; 409 stale with the current version in `details`; 403 not a signer; 403 `email_not_verified`; 422 wrong typed name with the expected name in the message), edit (`EditRequest`, returns invalidated founders); the signing founder always comes from the session, a `founder_id` in the body is rejected as an unknown field.
4. `/pdf` returns `application/pdf` for executed documents (409 `not_executed` otherwise), `/docx` returns the Word MIME type; both gated by plan; file names per T-015.
5. Audit oldest first, including rejected attempts.
6. Website: `GET` latest (`null` when none); `POST build` -> 202 `SiteJobOutcome` (409 `name_not_chosen`); `POST deploy` -> 202 (409 `qa_failed_needs_override` without override; 402 on Free); preview serves files with the right content type and the sandbox CSP; unknown path -> 404; download returns `application/zip`.
7. Routes contain no business logic (one service call each).

## Feature run (`evidence/T-017/feature_run.py`)

Builds services with fakes and `InlineJobRunner` on a temp DB, prepares a locked
two-founder company with Alice and Bob as verified, linked members, then over HTTP with
two logged-in `TestClient` sessions: fetches the cap table and downloads; generates
documents; Alice e-signs; Bob edits; Alice retries the stale version (prints the 409);
a third user gets 404; everyone signs; downloads a signed PDF and a Word copy (sizes);
prints the audit trail; builds the website (prints the job and QA rounds), fetches the
preview head and CSP, deploys to the fake host and prints the URL; repeats generate and
deploy for a Free-plan owner and prints the 402 bodies.

## Out of scope

Composition and the app (T-016), case/chat routes (T-041), UI (wave 4).
