# T-023: End-to-end customer journey: API test suite, browser journey and the run guide

| | |
|---|---|
| **Wave** | 5 |
| **Depends on** | T-018, T-019, T-020, T-021, T-022, T-034, T-036, T-042, T-043, T-044, T-045 |
| **ADRs** | [ADR-0003](../docs/adr/0003-merge-gate-tests-and-recorded-run.md), [ADR-0005](../docs/adr/0005-frontend-verification-and-browser-recordings.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md) |
| **Status** | todo |

## Goal

Prove the product's definition of done: a new customer finds the landing page, chooses a
plan and pays (test mode), signs up, invites a co-founder, and goes from a first chat
message to a verified name and domain choice, documents executed with electronic
signatures, a cap table, a QA-passed live (or packaged) website and a registration
checklist, through the API and the UI, with every outside service faked; and give the
owner a plain guide to run the product.

## Owns (only these paths may change)

- `tests/test_e2e_journey.py`
- `tests/test_e2e_security.py`
- `docs/running-the-app.md`
- `evidence/T-023/`
- `prs/T-023.md`

## Contracts

- **Provides:** the journey and security test suites, the recorded browser journey, and `docs/running-the-app.md` (start the app locally; `LLM_PROVIDER` choices with the `claude_code` own-machine-only rule and `anthropic` for production; live RDAP, Netlify, Stripe test mode, SMTP; demo mode; the demo video command from T-046 once it exists; first-release limits: not legal advice, no filing or domain buying, built-in e-signatures).
- **Consumes:** the whole product (T-001..T-045), `running_app`/`login`/`capture_matrix` (T-011), seeding (T-016).

## Acceptance criteria

1. `tests/test_e2e_journey.py` drives everything through `TestClient` from an empty database using only HTTP calls a customer would make: plans -> sign-up (Alice) -> verify email from the outbox -> checkout with the fake gateway -> Launch active -> create company -> chat journey (facts with the default-vesting note, Law/Name/Website/Guide handovers and returns) -> invite Bob -> Bob signs up and accepts -> documents generated -> Alice e-signs -> Bob edits and e-signs (Alice invalidated) -> a stale signature rejected -> both sign -> `legal_complete` -> signed PDF downloads -> cap table totals 10,000,000 and matches the documents -> website job with one QA fix round deployed to the fake host -> second company (within the plan limit) with hosting not configured ends "packaged" -> checklist complete, progress 100 % -> data export contains both companies -> cancel in the fake portal -> Free plan blocks new documents but executed PDFs still download.
2. One failure path per step with friendly messages: equity not 100, a taken `.com`, a stale signature, a wrong typed name, an unverified signer, a QA failure needing explicit override, a guide request before the state is known, a Free-plan publish.
3. `tests/test_e2e_security.py`: for every company route, an anonymous call is 401 and another customer gets 404; unsafe calls without CSRF are 403; login is rate limited; responses never contain password hashes, raw tokens or another customer's data; `APP_ENV=production` with `claude_code` or fake services refuses to start.
4. The recorded run drives the same journey in the browser (landing -> pricing -> sign-up -> test checkout -> onboarding -> chat -> invite -> Bob in a second context -> e-signatures -> downloads -> website -> guide -> settings export) and saves the screenshot matrix for every view at the end state.
5. When `LAUNCH_TEST_POSTGRES_URL` is set, the API journey also runs on PostgreSQL.
6. If the journey reveals a defect in another ticket's code, the builder reports `BLOCKED` with the failing assertion instead of editing that code.

## Feature run (`evidence/T-023/feature_run.py`)

Builds the frontend, starts `running_app()` with fake services and demo mode off, and
plays the browser journey of criterion 4 as Alice and Bob (two browser contexts),
printing each step and asserting what is visible; saves the matrices of every view; then
prints a definition-of-done table (each item of the brief's "Definition of done" with
PASS) and the run guide's section headings.

## Out of scope

New features or fixes in other tickets' files; the demo video (T-046).
