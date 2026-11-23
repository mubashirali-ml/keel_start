# T-001: Foundation: package skeleton, shared and cross-cutting contracts, schema, fakes and typed stubs

| | |
|---|---|
| **Wave** | 0 |
| **Depends on** | — |
| **ADRs** | [ADR-0038](../docs/adr/0038-plans-v2-free-launch-team-and-plan-settings.md), [ADR-0039](../docs/adr/0039-brand-charterly-everywhere-customers-look.md), [ADR-0024](../docs/adr/0024-stack-and-module-layout-v2.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0025](../docs/adr/0025-dependency-set-v2-python-and-npm.md), [ADR-0026](../docs/adr/0026-accounts-sessions-request-context-and-authorization.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0029](../docs/adr/0029-transactional-email-notifications-and-83b-reminders.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0031](../docs/adr/0031-electronic-signatures-and-signed-pdfs.md), [ADR-0032](../docs/adr/0032-services-and-http-api-v2.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0036](../docs/adr/0036-ui-recorded-runs-with-accounts-and-demo-seeding-v2.md), [ADR-0008](../docs/adr/0008-shared-domain-contracts.md), [ADR-0009](../docs/adr/0009-agent-message-and-handoff-protocol.md), [ADR-0010](../docs/adr/0010-llm-provider-abstraction-and-fake.md), [ADR-0011](../docs/adr/0011-external-service-ports-rdap-and-hosting.md), [ADR-0013](../docs/adr/0013-case-validation-cap-table-and-vesting-rules.md), [ADR-0014](../docs/adr/0014-founding-documents-and-signoff-state-machine.md), [ADR-0015](../docs/adr/0015-website-generation-qa-and-deploy-loop.md), [ADR-0016](../docs/adr/0016-registration-guide-data-and-checklist.md) |
| **Status** | escalated |

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
  - `config.py`: `AppEnv`, `Settings` (every field of ADR-0021 plus the ADR-0038 billing settings: Team price ids, `billing_yearly_enabled`, `plan_amounts` from the `PLAN_*` variables, `support_email`; `model_for`, `effort_for`, `plans()`, redacting `__repr__`), `ConfigError`, `load_settings(env=None)` with per-environment defaults and **all production guards** (ADR-0021).
  - `reliability.py`: `RetryPolicy`, `is_transient`, `RetryableError`, `call_with_retry`, `Deadline` (ADR-0023).
  - `domain/`: everything in ADR-0008/0009/0013/0014/0015/0016 as before, plus `domain/accounts.py` (ADR-0026: `User`, `MemberRole`, `Membership`, `Invite`, `Permission`, `RequestContext`, `Actor`, `CaseAccess` incl. `require`, `require_feature`, `system`), `domain/billing.py` (ADR-0038, replacing the ADR-0030 plan types: `PlanId` with `FREE`/`LAUNCH`/`TEAM`, `SupportLevel`, `PlanAmounts`, `DEFAULT_PLAN_AMOUNTS`, `Plan` incl. `rank`, `yearly_available`, `support`, `support_label`, `highlights`, `build_plans`, `PLANS`, `lowest_plan_with`, `next_plan_for_companies`, `Entitlements` incl. `support` and `for_plan(plan, plans=PLANS)`, `UsageSummary`, `PriceCheck`; unchanged from ADR-0030: `BillingInterval`, `Feature`, `SubscriptionStatus`, `Subscription`, `CheckoutSession`, `PaymentEvent`), `domain/jobs.py` (ADR-0028: `JobStatus`, `JobKind`, `JobRecord`, `JobContext`, `JobHandler`, `RetryableJobError`), `domain/email.py` (ADR-0029: `EmailTemplate`, `EmailMessage`, `SendResult`), the ADR-0031 changes (`SignatureEvidence`, the new `Signature`, new `AuditAction` values, `ESIGN_CONSENT_TEXT`/`ESIGN_CONSENT_VERSION`, `document_sha256`, `names_match`), `BRAND_NAME = "Charterly"` in `constants.py` (ADR-0039, confirmed by the owner), `CaseRecord.created_by` / `billing_user_id` (ADR-0027), every new error in ADR-0026 plus `RetryableError`, and the ADR-0032 views (`CaseView` additions, `PostMessageResult.jobs`, `SiteJobOutcome`, `MeView`, `MemberView`, `InvitePreview`, `PublicConfig` incl. the ADR-0038 `support_email` and `yearly_enabled`, `BillingOverview`, `SignRequest`, `EditRequest`).
  - `llm/`: `LLMMessage`, `LLMRequest`, `LLMProvider`, `FakeLLM`, `FakeLLMMissingHandler` (ADR-0010), `llm/usage.py` (`LLMUsage`, `report_usage`, `usage_sink`, ADR-0022), `get_llm(settings)` implementing the ADR-0022 selection table (it constructs the provider classes; their behaviour is stubbed).
  - `ports/`: `DomainChecker`, `FakeDomainChecker`, `DEFAULT_FAKE_TAKEN`, `SiteHost`, `FakeSiteHost`, `UnconfiguredSiteHost` (ADR-0011); `EmailSender`, `FakeEmailSender`, `Mailer`, `RecordingMailer` (ADR-0029); `Notifier`, `RecordingNotifier`; `PaymentGateway` incl. the ADR-0038 `change_subscription_price` and `price_amount`, `FakePaymentGateway` (incl. `complete_checkout`, `cancel`, `change_subscription_price`, `price_amount` answering from the settings' amounts, own signed webhook payloads), `EntitlementsProvider`, `StaticEntitlements`, `UsageCounter` (ADR-0030, ADR-0038); `JobRunner`, `JobRegistry`, `InlineJobRunner` (ADR-0028).
  - `persistence/tables.py`: every table of ADR-0027 on one `MetaData` with a naming convention; `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_initial.py` creating exactly that schema; `alembic.ini` reading the URL from settings.
  - `agents/base.py` (ADR-0009 types), `agents/manager/greeting.py: manager_greeting()` (as before, copy now uses `BRAND_NAME`: "the Manager at Charterly", ADR-0039), `agents/{manager,law,name,website,qa,guide}/fake.py` with empty `FAKE_HANDLERS`.
  - `workflows/ports.py`: `LegalServicePort`, `WebsiteServicePort` with the ADR-0032 signatures.
  - `api/app.py`: skeleton `create_app(services=None, settings=None)` serving `GET /api/health` (`{status: "ok"}`), the error envelope for every `LaunchError` (incl. the new codes, `request_id` in 500 bodies), and the SPA static mount; `api/deps.py: get_services`; `api/routes/{cases,jobs,legal,website,auth,account,team,billing,admin}.py` each with an empty `router = APIRouter()`; `api/middleware.py`, `api/schemas.py` stubs.
- **Provides (typed stubs: exact signature + docstring citing the ADR, body `raise NotImplementedError`):** everything listed per owner in ADR-0024, in particular: `rules/*` (T-002, T-003); `signoff/machine.py` with the ADR-0031 `sign`/`edit` signatures (T-004); `persistence/engine.py` (`create_db_engine`, `init_db`, `schema_is_current`) and `persistence/repository.py` `Repository` with the ADR-0027 method list (T-005); `persistence/{accounts,team,email_outbox,billing,jobs,limits,privacy,admin}.py` repository classes (T-026, T-027, T-028, T-029, T-030, T-032, T-037, T-038); `accounts/` (`hash_password`, `verify_password`, `needs_rehash`, `check_password_policy`, `AuthService`, `SessionToken`), `team/` (`TeamService`), `access/` (`ROLE_PERMISSIONS` real, `authorize_case` stub) (ADR-0026); `email/` (`render_email`, `TEMPLATE_DATA_KEYS`, `OutboxMailer`, `send_outbox_email`, `ConsoleEmailSender`, `FileDropEmailSender`), `adapters/smtp_email.py` (ADR-0029); `billing/` (`BillingService` with the ADR-0038 constructor and methods incl. `overview`, `change_plan`, `check_prices`; `DbEntitlements(billing, plans)`, `price_id_for`, `plan_for_price`), `adapters/stripe_payments.py` `StripePaymentGateway(settings, *, client=None)` (ADR-0030, ADR-0038); `jobs/` (`DbJobRunner`, `Worker`, `Scheduler`, `start_embedded_worker`, `__main__`) (ADR-0028); `pdf/` (`SignerInfo`, `render_signed_pdf`, `render_docx` both with the ADR-0039 keyword `brand_name`, `markdown_blocks`) (ADR-0031, ADR-0039); `security/` (`issue_csrf_token`, `check_csrf`, security headers, `RateLimitRule`, `RATE_LIMITS`, `RateLimiter`, `MeteredLLM`, `ScrubResult`, `scrub`) (ADR-0033); `observability/` (`configure_logging`, `RequestContextMiddleware`, `log_context`, `ErrorReporter`, `load_error_reporter`, `report_error`) (ADR-0034); `llm/claude_code.py` `ClaudeCodeProvider`, `find_claude_binary` (T-024); `llm/anthropic_provider.py` `AnthropicProvider`, `llm/openai_compat.py` `OpenAICompatibleProvider(settings, *, preset=None, chat_model=None)` (T-025); all agent, orchestrator, pipeline and workflow stubs as before with the ADR-0032 signatures; `notifications/` (`EmailNotifier`, `ReminderSweep`), `privacy/` (`PrivacyService`, `DeletionReport`), `admin/` (`AdminService` with the ADR-0038 `plan` filter on `users` and the `price_checks` callable, row models, `Page`, `SystemInfo` incl. `price_checks`, `__main__`) (ADR-0029, ADR-0034, ADR-0038); `composition.py` `Services` (real dataclass, ADR-0032 fields) + `build_services` (stub); `demo/` `DEMO_STAGES`, `SeedResult`, `seed_case` (ADR-0036); `devtools/ui_run.py` (ADR-0036 signatures, incl. `login`, `DEMO_PASSWORD`).
- **Provides (tests):** `pytest.ini` (`testpaths = tests`, `addopts = -q`, marker `postgres`); `tests/conftest.py` fixtures from ADR-0007 (`fake_llm`, `fake_domain_checker`, `fake_site_host`, `today`, `sample_facts`, `repo`) plus ADR-0024's (`settings`, `engine`, `inline_jobs`, `fake_mailer`, `fake_notifier`, `fake_payments`, `entitlements_launch`, `entitlements_free`, `entitlements_team`, `request_ctx`, `system_access`); fixtures needing a stubbed module skip instead of erroring; a collection hook that skips tests importing a not-yet-installed ADR-0025 package with the reason "package X not installed (ADR-0025)".
- **Consumes:** nothing.

## Acceptance criteria

1. Every module in the ADR-0024 layout imports cleanly (also before the ADR-0025 packages are installed: imports of `alembic`, `psycopg`, `argon2`, `stripe`, `reportlab`, `docx`, `email_validator` inside stubs are lazy); `tests/test_foundation.py` imports each one.
2. All domain models match the ADRs field for field and round-trip through `model_dump(mode="json")` / `model_validate`; `ChatMessage` with `role=agent` and no `agent` is rejected.
3. `apply_patch`, helpers, `AGENT_PROFILES`, `handoff_message`, `SiteBundle.to_zip`, `US_STATES`, `FakeLLM` and `FakeDomainChecker`/`FakeSiteHost`/`UnconfiguredSiteHost` behave exactly as in the previous T-001 criteria (ADR-0008/0009/0010/0011): founder matching id -> email -> name, `f1..` ids never reused, `C_CORP` forces `DE`, `deadline_83b(2026-12-01) == 2026-12-31`, month-end clamping, `slugify("Crumb & Co.") == "crumb-co"`, `domain_label("Crumb Ledger LLC") == "crumbledger"`, byte-identical zips, 51 states with https URLs, script > handler > default resolution, `FakeLLMMissingHandler`, schema validation raising `LLMOutputError`.
4. `document_sha256` normalises line endings (CRLF and LF content hash equal); `names_match("alice  chen", "Alice Chen.")` is true and `("Alice", "Alice Chen")` false.
5. `load_settings`: per-environment defaults of ADR-0021; LLM selection of ADR-0022 (anthropic key -> anthropic; deepseek; groq; none -> fake; `claude_code` only when explicit; `LAUNCH_FAKE_SERVICES=1` forces fake); `LLM_MODEL_QA` etc. populate `llm_models` and `model_for("qa.review")`; **production guards**: one `ConfigError` listing every problem for a production env with `claude_code`, fake payments, console email, SQLite, short secret, http base URL, demo mode, a missing Team price id, a missing `SUPPORT_EMAIL` and a paid plan priced at 0; a correct production env loads (yearly price ids are not required when `BILLING_YEARLY_ENABLED=false`). Secrets never appear in `repr(settings)`.
6. `RequestContext.require_user` raises `AuthRequiredError` without a user; `CaseAccess.require` raises `ForbiddenError` for a missing permission; `require_feature` raises `PlanRequiredError` on Free for `ESIGN`; `CaseAccess.system` has every permission and actor `"system"`; `Actor.audit_actor` prefers founder id, then user id.
7. `PLANS` and `Entitlements.for_plan` match the ADR-0038 table for Free, Launch and Team (prices, yearly = 10 x monthly, companies, AI messages, features, support level and label); `PLAN_TEAM_AI_MESSAGES=20000` changes only that number in `Settings.plans()` and in the highlights; `BILLING_YEARLY_ENABLED=false` sets `yearly_available` false on every plan; `lowest_plan_with(Feature.ESIGN)` is Launch; `next_plan_for_companies` goes Free -> Launch -> Team -> None; `require_feature` on Free puts `required_plan: "launch"` in the error details; `StaticEntitlements` returns the configured plan.
8. `InlineJobRunner`: `enqueue` runs the registered handler at once, records `succeeded` with the result; a handler raising `RetryableJobError` twice then succeeding ends `succeeded` with `attempts == 3`; a plain exception ends `failed` with a friendly `error`; `dedupe_key` returns the existing job; unknown kind fails clearly.
9. `RecordingMailer` records and deduplicates; `FakeEmailSender.fail_next` returns transient failures; `FakePaymentGateway` produces checkout URLs under `{app_base_url}/app/billing/test-checkout`, and `complete_checkout` / `cancel` / `change_subscription_price` events parse back through its own `parse_webhook` (the last one carrying the new price id), while a tampered payload raises `WebhookSignatureError`.
10. `call_with_retry` retries only transient errors, honours attempts and backoff with an injected `sleep`, and `Deadline` expires.
11. `usage_sink` collects `LLMUsage` reported inside its block (also nested) and nothing outside it; `FakeLLM` reports one usage per call.
12. Schema: `alembic upgrade head` on a fresh SQLite file creates every ADR-0027 table and column, and the autogenerate comparison against `tables.py` is empty (test runs only when `alembic` is installed; otherwise skipped with the ADR-0025 reason).
13. Every stub exists with the exact ADR signature (checked with `inspect.signature` for parameter names; the test must NOT assert `NotImplementedError`).
14. `create_app()` with no services: `/api/health` returns `{status: "ok"}`; a route raising each new error renders the envelope with the ADR-0026 status; SPA fallback serves `index.html` for `/app/x` and a JSON 404 for `/api/nope`.
15. `.env.example` lists every ADR-0021 variable with a comment, grouped (core, LLM, services, email, payments incl. the four Stripe price ids, `BILLING_YEARLY_ENABLED`, every `PLAN_*` override commented out with its default, and `SUPPORT_EMAIL`, data, security, operations), `BRAND_NAME=Charterly`, including commented `LLM_MODEL_NAME=claude-haiku-5-5` / `LLM_MODEL_QA=claude-haiku-5-5`, and no real secrets.
16. Brand guard (ADR-0039): a test scans `launch_agents/` and finds the literal "Charterly" only in `domain/constants.py`.
17. `bash scripts/py.sh -m pytest` passes with no network access.

## Feature run (`evidence/T-001/feature_run.py`)

Prints and asserts, without network: settings resolution for five env maps (fake,
anthropic with per-agent Haiku models, deepseek, claude_code in development, and a
production map that fails with the full `ConfigError` list; keys redacted); a `FakeLLM`
call inside a `usage_sink` with the collected usage; `apply_patch` on sample facts; the
83(b) deadline; handoff messages; a `CaseAccess` for a member and for the system with
their permissions and a `PlanRequiredError` on Free; an `InlineJobRunner` job that is
retried then succeeds; a `RecordingMailer` dedupe; a fake checkout -> webhook event round
trip and a Launch -> Team price change event; the three plans from `Settings.plans()` with one `PLAN_*` override; `document_sha256` of a document; the migrated table list of a temp SQLite DB (or
the skip reason); `GET /api/health`; and the list of stubs with their signatures.

## Out of scope

Implementing any stubbed behaviour (rules, sign-off, repositories, auth, team, email,
billing, jobs, PDF, security, observability, agents, graph, services, real API routes,
providers other than the fake, frontend).

## Escalation (2026-11-23): keep the scope, finish the merge

Decision: T-001 is **not** re-scoped, split or dropped. The Reviewer approved it in round 3
with no blocking findings, and the changes after approval touch no T-001 code (a merge of the
harness-only commit `71fd333`, a re-recorded `evidence/T-001/run.log`, a note in `prs/T-001.md`).
The escalation came from the delivery loop, not from a defect: the gate agent was not allowed to
run `bash scripts/merge_pr.sh T-001`, the gate-fix step then cleared the approval, and the three
review rounds were already used.

Two things stand between the approved branch and `main`:

1. **Round count in `prs/T-001.md`.** The gate counts every `### Round N` heading in the file,
   and the "Builder response" section uses `### Round 1` / `### Round 2` too, so the gate sees
   5 rounds and refuses ("5 review rounds > 3"). The Builder renames its own two headings to a
   form that does not start with `### Round` (for example `#### Reply to review round 1`),
   changes nothing else, and commits `T-001: rename builder reply headings for the gate`. That
   is a PR-record change only; no new review round is needed or allowed (a fourth `### Round`
   would fail the gate again). Later builders follow the same rule: the `### Round N` heading
   belongs only to the Reviewer, under "## Review".
2. **Permission to run the gate.** A human runs `bash scripts/merge_pr.sh T-001` once from the
   main checkout, or allows that command for the gate agent. Re-running the whole delivery loop
   for T-001 does not help: it would start a fourth review round.

After the merge, T-001's status becomes `merged` and wave 1 starts as planned.

Raised during review, not blocking T-001 and handled separately in a later Supervisor pass:
ADR-0008 says founder ids are never reused, but `apply_patch` can only guarantee that within one
patch (`CaseFacts` keeps no high-water mark).

## Delivery run closed (2026-11-23): still escalated, not merged

The delivery run for waves 0 and 1 ended with T-001 escalated after 3 review rounds (last
verdict APPROVED in round 3). At close, `ticket/T-001` still has the Builder's own
`### Round 1` / `### Round 2` reply headings in `prs/T-001.md`, so the gate would still count
5 rounds, and `scripts/merge_pr.sh T-001` has not been run. The decision above stands: no
re-scope, no new review round. Remaining steps, in order:

1. Builder: rename the two reply headings under "## Builder response" (nothing else) and
   commit `T-001: rename builder reply headings for the gate`.
2. A human runs `bash scripts/merge_pr.sh T-001` once from the main checkout (or permits that
   command for the gate agent).

Wave 1 (T-002 to T-011, T-024 to T-033) did not start, because every wave-1 ticket depends on
T-001 being on `main`. Those tickets stay `todo` with unchanged scope; the next delivery run
starts wave 1 once T-001 is `merged`.
