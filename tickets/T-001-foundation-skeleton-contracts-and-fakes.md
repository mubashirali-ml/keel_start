# T-001: Foundation: package skeleton, shared and cross-cutting contracts, schema, fakes and typed stubs

| | |
|---|---|
| **Wave** | 0 |
| **Depends on** | — |
| **ADRs** | [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md) |
| **Status** | todo |

## Goal

Every later ticket can be built and tested in parallel, and later waves add features
without refactoring earlier ones: the whole `launch_agents/` package exists with the
shared domain types, the cross-cutting contracts (settings with `APP_ENV`, the
request context / account / company-membership types every service receives, the email,
notification, payment, entitlement and job-runner ports with fakes), the complete
database schema with its first migration, the LLM abstraction with the deterministic fake
and provider selection, and exact typed stubs for every function one ticket calls in another.

## Owns (only these paths may change)

- `launch_agents/`
- `migrations/`
- `alembic.ini`
- `tests/conftest.py`
- `tests/test_foundation.py`
- `pytest.ini`
- `.env.example`
- `evidence/T-001/`
- `prs/T-001.md`

## Contracts

- **Provides (implemented):**
  - `config.py`: `AppEnv`, `Settings` (every field of ADR-0021, `model_for`, `effort_for`, redacting `__repr__`), `ConfigError`, `load_settings(env=None)` with per-environment defaults and **all production guards** (ADR-0021).
  - `reliability.py`: `RetryPolicy`, `is_transient`, `RetryableError`, `call_with_retry`, `Deadline` (ADR-0023).
  - `domain/`: everything in ADR-0008/0009/0013/0014/0015/0016 as before, plus `domain/accounts.py` (ADR-0026: `User`, `MemberRole`, `Membership`, `Invite`, `Permission`, `RequestContext`, `Actor`, `CaseAccess` incl. `require`, `require_feature`, `system`), `domain/billing.py` (ADR-0030: `PlanId`, `BillingInterval`, `Feature`, `Plan`, `PLANS` with the default prices, `Entitlements` incl. `for_plan`, `SubscriptionStatus`, `Subscription`, `CheckoutSession`, `PaymentEvent`), `domain/jobs.py` (ADR-0028: `JobStatus`, `JobKind`, `JobRecord`, `JobContext`, `JobHandler`, `RetryableJobError`), `domain/email.py` (ADR-0029: `EmailTemplate`, `EmailMessage`, `SendResult`), the ADR-0031 changes (`SignatureEvidence`, the new `Signature`, new `AuditAction` values, `ESIGN_CONSENT_TEXT`/`ESIGN_CONSENT_VERSION`, `document_sha256`, `names_match`), `BRAND_NAME = "Charterly"` in `constants.py` (ADR-0035, pending Q-007), `CaseRecord.created_by` / `billing_user_id` (ADR-0027), every new error in ADR-0026 plus `RetryableError`, and the ADR-0032 views (`CaseView` additions, `PostMessageResult.jobs`, `SiteJobOutcome`, `MeView`, `MemberView`, `InvitePreview`, `PublicConfig`, `SignRequest`, `EditRequest`).
  - `llm/`: `LLMMessage`, `LLMRequest`, `LLMProvider`, `FakeLLM`, `FakeLLMMissingHandler` (ADR-0010), `llm/usage.py` (`LLMUsage`, `report_usage`, `usage_sink`, ADR-0022), `get_llm(settings)` implementing the ADR-0022 selection table (it constructs the provider classes; their behaviour is stubbed).
  - `ports/`: `DomainChecker`, `FakeDomainChecker`, `DEFAULT_FAKE_TAKEN`, `SiteHost`, `FakeSiteHost`, `UnconfiguredSiteHost` (ADR-0011); `EmailSender`, `FakeEmailSender`, `Mailer`, `RecordingMailer` (ADR-0029); `Notifier`, `RecordingNotifier`; `PaymentGateway`, `FakePaymentGateway` (incl. `complete_checkout`, `cancel`, own signed webhook payloads), `EntitlementsProvider`, `StaticEntitlements` (ADR-0030); `JobRunner`, `JobRegistry`, `InlineJobRunner` (ADR-0028).
  - `persistence/tables.py`: every table of ADR-0027 on one `MetaData` with a naming convention; `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_initial.py` creating exactly that schema; `alembic.ini` reading the URL from settings.
  - `agents/base.py` (ADR-0009 types), `agents/manager/greeting.py: manager_greeting()` (as before, copy now uses `BRAND_NAME`), `agents/{manager,law,name,website,qa,guide}/fake.py` with empty `FAKE_HANDLERS`.
  - `workflows/ports.py`: `LegalServicePort`, `WebsiteServicePort` with the ADR-0032 signatures.
  - `api/app.py`: skeleton `create_app(services=None, settings=None)` serving `GET /api/health` (`{status: "ok"}`), the error envelope for every `LaunchError` (incl. the new codes, `request_id` in 500 bodies), and the SPA static mount; `api/deps.py: get_services`; `api/routes/{cases,jobs,legal,website,auth,account,team,billing,admin}.py` each with an empty `router = APIRouter()`; `api/middleware.py`, `api/schemas.py` stubs.
- **Provides (typed stubs: exact signature + docstring citing the ADR, body `raise NotImplementedError`):** everything listed per owner in ADR-0024, in particular: `rules/*` (T-002, T-003); `signoff/machine.py` with the ADR-0031 `sign`/`edit` signatures (T-004); `persistence/engine.py` (`create_db_engine`, `init_db`, `schema_is_current`) and `persistence/repository.py` `Repository` with the ADR-0027 method list (T-005); `persistence/{accounts,team,email_outbox,billing,jobs,limits,privacy,admin}.py` repository classes (T-026, T-027, T-028, T-029, T-030, T-032, T-037, T-038); `accounts/` (`hash_password`, `verify_password`, `needs_rehash`, `check_password_policy`, `AuthService`, `SessionToken`), `team/` (`TeamService`), `access/` (`ROLE_PERMISSIONS` real, `authorize_case` stub) (ADR-0026); `email/` (`render_email`, `TEMPLATE_DATA_KEYS`, `OutboxMailer`, `send_outbox_email`, `ConsoleEmailSender`, `FileDropEmailSender`), `adapters/smtp_email.py` (ADR-0029); `billing/` (`BillingService`, `DbEntitlements`, `price_id_for`), `adapters/stripe_payments.py` `StripePaymentGateway(settings, *, client=None)` (ADR-0030); `jobs/` (`DbJobRunner`, `Worker`, `Scheduler`, `start_embedded_worker`, `__main__`) (ADR-0028); `pdf/` (`SignerInfo`, `render_signed_pdf`, `render_docx`, `markdown_blocks`) (ADR-0031); `security/` (`issue_csrf_token`, `check_csrf`, security headers, `RateLimitRule`, `RATE_LIMITS`, `RateLimiter`, `MeteredLLM`, `ScrubResult`, `scrub`) (ADR-0033); `observability/` (`configure_logging`, `RequestContextMiddleware`, `log_context`, `ErrorReporter`, `load_error_reporter`, `report_error`) (ADR-0034); `llm/claude_code.py` `ClaudeCodeProvider`, `find_claude_binary` (T-024); `llm/anthropic_provider.py` `AnthropicProvider`, `llm/openai_compat.py` `OpenAICompatibleProvider(settings, *, preset=None, chat_model=None)` (T-025); all agent, orchestrator, pipeline and workflow stubs as before with the ADR-0032 signatures; `notifications/` (`EmailNotifier`, `ReminderSweep`), `privacy/` (`PrivacyService`, `DeletionReport`), `admin/` (`AdminService`, row models, `Page`, `SystemInfo`, `__main__`) (ADR-0029, ADR-0034); `composition.py` `Services` (real dataclass, ADR-0032 fields) + `build_services` (stub); `demo/` `DEMO_STAGES`, `SeedResult`, `seed_case` (ADR-0036); `devtools/ui_run.py` (ADR-0036 signatures, incl. `login`, `DEMO_PASSWORD`).
- **Provides (tests):** `pytest.ini` (`testpaths = tests`, `addopts = -q`, marker `postgres`); `tests/conftest.py` fixtures from ADR-0007 (`fake_llm`, `fake_domain_checker`, `fake_site_host`, `today`, `sample_facts`, `repo`) plus ADR-0024's (`settings`, `engine`, `inline_jobs`, `fake_mailer`, `fake_notifier`, `fake_payments`, `entitlements_launch`, `entitlements_free`, `request_ctx`, `system_access`); fixtures needing a stubbed module skip instead of erroring; a collection hook that skips tests importing a not-yet-installed ADR-0025 package with the reason "package X not installed (ADR-0025)".
- **Consumes:** nothing.

## Acceptance criteria

1. Every module in the ADR-0024 layout imports cleanly (also before the ADR-0025 packages are installed: imports of `alembic`, `psycopg`, `argon2`, `stripe`, `reportlab`, `docx`, `email_validator` inside stubs are lazy); `tests/test_foundation.py` imports each one.
2. All domain models match the ADRs field for field and round-trip through `model_dump(mode="json")` / `model_validate`; `ChatMessage` with `role=agent` and no `agent` is rejected.
3. `apply_patch`, helpers, `AGENT_PROFILES`, `handoff_message`, `SiteBundle.to_zip`, `US_STATES`, `FakeLLM` and `FakeDomainChecker`/`FakeSiteHost`/`UnconfiguredSiteHost` behave exactly as in the previous T-001 criteria (ADR-0008/0009/0010/0011): founder matching id -> email -> name, `f1..` ids never reused, `C_CORP` forces `DE`, `deadline_83b(2026-12-01) == 2026-12-31`, month-end clamping, `slugify("Crumb & Co.") == "crumb-co"`, `domain_label("Crumb Ledger LLC") == "crumbledger"`, byte-identical zips, 51 states with https URLs, script > handler > default resolution, `FakeLLMMissingHandler`, schema validation raising `LLMOutputError`.
4. `document_sha256` normalises line endings (CRLF and LF content hash equal); `names_match("alice  chen", "Alice Chen.")` is true and `("Alice", "Alice Chen")` false.
5. `load_settings`: per-environment defaults of ADR-0021; LLM selection of ADR-0022 (anthropic key -> anthropic; deepseek; groq; none -> fake; `claude_code` only when explicit; `LAUNCH_FAKE_SERVICES=1` forces fake); `LLM_MODEL_QA` etc. populate `llm_models` and `model_for("qa.review")`; **production guards**: one `ConfigError` listing every problem for a production env with `claude_code`, fake payments, console email, SQLite, short secret, http base URL and demo mode; a correct production env loads. Secrets never appear in `repr(settings)`.
6. `RequestContext.require_user` raises `AuthRequiredError` without a user; `CaseAccess.require` raises `ForbiddenError` for a missing permission; `require_feature` raises `PlanRequiredError` on Free for `ESIGN`; `CaseAccess.system` has every permission and actor `"system"`; `Actor.audit_actor` prefers founder id, then user id.
7. `PLANS` and `Entitlements.for_plan` match ADR-0030; `StaticEntitlements` returns the configured plan.
8. `InlineJobRunner`: `enqueue` runs the registered handler at once, records `succeeded` with the result; a handler raising `RetryableJobError` twice then succeeding ends `succeeded` with `attempts == 3`; a plain exception ends `failed` with a friendly `error`; `dedupe_key` returns the existing job; unknown kind fails clearly.
9. `RecordingMailer` records and deduplicates; `FakeEmailSender.fail_next` returns transient failures; `FakePaymentGateway` produces checkout URLs under `{app_base_url}/app/billing/test-checkout`, and `complete_checkout` / `cancel` events parse back through its own `parse_webhook`, while a tampered payload raises `WebhookSignatureError`.
10. `call_with_retry` retries only transient errors, honours attempts and backoff with an injected `sleep`, and `Deadline` expires.
11. `usage_sink` collects `LLMUsage` reported inside its block (also nested) and nothing outside it; `FakeLLM` reports one usage per call.
12. Schema: `alembic upgrade head` on a fresh SQLite file creates every ADR-0027 table and column, and the autogenerate comparison against `tables.py` is empty (test runs only when `alembic` is installed; otherwise skipped with the ADR-0025 reason).
13. Every stub exists with the exact ADR signature (checked with `inspect.signature` for parameter names; the test must NOT assert `NotImplementedError`).
14. `create_app()` with no services: `/api/health` returns `{status: "ok"}`; a route raising each new error renders the envelope with the ADR-0026 status; SPA fallback serves `index.html` for `/app/x` and a JSON 404 for `/api/nope`.
15. `.env.example` lists every ADR-0021 variable with a comment, grouped (core, LLM, services, email, payments, data, security, operations), including commented `LLM_MODEL_NAME=claude-haiku-5-5` / `LLM_MODEL_QA=claude-haiku-5-5`, and no real secrets.
16. `bash scripts/py.sh -m pytest` passes with no network access.

## Feature run (`evidence/T-001/feature_run.py`)

Prints and asserts, without network: settings resolution for five env maps (fake,
anthropic with per-agent Haiku models, deepseek, claude_code in development, and a
production map that fails with the full `ConfigError` list; keys redacted); a `FakeLLM`
call inside a `usage_sink` with the collected usage; `apply_patch` on sample facts; the
83(b) deadline; handoff messages; a `CaseAccess` for a member and for the system with
their permissions and a `PlanRequiredError` on Free; an `InlineJobRunner` job that is
retried then succeeds; a `RecordingMailer` dedupe; a fake checkout -> webhook event round
trip; `document_sha256` of a document; the migrated table list of a temp SQLite DB (or
the skip reason); `GET /api/health`; and the list of stubs with their signatures.

## Out of scope

Implementing any stubbed behaviour (rules, sign-off, repositories, auth, team, email,
billing, jobs, PDF, security, observability, agents, graph, services, real API routes,
providers other than the fake, frontend).
