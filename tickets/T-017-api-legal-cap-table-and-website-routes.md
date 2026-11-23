# T-017: HTTP API: cap table, documents and sign-off, audit, and website routes

| | |
|---|---|
| **Wave** | 3 |
| **Depends on** | T-005, T-013, T-015 |
| **ADRs** | [ADR-0017](../docs/adr/0017-services-and-http-api-surface.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md) |
| **Status** | todo |

## Goal

Over HTTP, founders can view and download the cap table, generate, sign and edit the
founding documents (with stale-version protection), read the audit trail, and build,
preview, download and deploy the website.

## Owns (only these paths may change)

- `launch_agents/api/routes/legal.py`
- `launch_agents/api/routes/website.py`
- `tests/test_api_legal.py`
- `tests/test_api_website.py`
- `evidence/T-017/`
- `prs/T-017.md`

## Contracts

- **Provides:** the T-017 rows of the ADR-0017 endpoint table, as `router = APIRouter()` in each file, with their request body models defined in the same file.
- **Consumes:** `get_services` (T-001 `api/deps.py`), `LegalService` (T-015), `WebsiteService` (T-013), `Repository` (T-005), domain views and errors (T-001). T-016 (same wave) builds the composition root; tests here build `Services` by hand from the real wave-2 services with fakes and mount the routers on a `FastAPI()` with the T-001 error handlers.

## Acceptance criteria

1. Cap table JSON matches `CapTable`; `cap-table.csv` returns `text/csv` and `cap-table.xlsx` the Excel MIME type, both with `Content-Disposition: attachment; filename="<company-slug>-cap-table.<ext>"`; invalid facts -> 409 `facts_not_ready` envelope.
2. Documents: generate (409 when facts not locked), list, sign, edit; stale version -> 409 `stale_version` with the current version in `details`; non-signer -> 403; already signed -> 409; edit returns the invalidated founder ids.
3. Audit returns every entry oldest first, including rejected attempts.
4. Website: get latest (`null` when none), build (409 `name_not_chosen`), deploy (409 `qa_failed_needs_override` without override; deploys with `override_qa` and a founder id), preview serves `index.html`/`styles.css` with the right content type and the sandbox CSP header (ADR-0017), unknown preview path -> 404, download returns `application/zip`.
5. Routes contain no business logic (each calls one service method and returns its result).

## Feature run (`evidence/T-017/feature_run.py`)

Builds services with fakes on a temp DB, prepares a locked two-founder case with a chosen
name directly through the services, then over HTTP (`TestClient`): fetches the cap table
and both downloads (prints sizes and the CSV), generates documents, signs as Alice, edits
as Bob, retries Alice's stale signature (prints the 409 body), signs everything, prints
the audit trail; builds the website (prints QA rounds), fetches the preview HTML head and
CSP header, deploys to the fake host and prints the URL, downloads the zip.

## Out of scope

Case/chat/name/guide routes and app composition (T-016), UI (wave 4).
