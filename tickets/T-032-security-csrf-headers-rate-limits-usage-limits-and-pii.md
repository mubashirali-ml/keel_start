# T-032: Security: CSRF, security headers, rate limits, per-account AI usage limits and the sensitive-data scrubber

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0022](../docs/adr/0022-llm-providers-fake-claude-code-anthropic-deepseek-groq.md), [ADR-0030](../docs/adr/0030-plans-billing-stripe-and-entitlements.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md) |
| **Status** | todo |

## Goal

The building blocks that keep customers safe exist and are tested: forged cross-site
requests are rejected, every response carries strict security headers, login and AI
endpoints are rate limited, each account's AI usage is metered against its plan, and
tax ids or card numbers typed into the chat are removed before anything stores or sends them.

## Owns (only these paths may change)

- `launch_agents/security/`
- `launch_agents/persistence/limits.py`
- `tests/test_security.py`
- `tests/test_rate_limits.py`
- `tests/test_metering.py`
- `tests/test_pii.py`
- `evidence/T-032/`
- `prs/T-032.md`

## Contracts

- **Provides:** `issue_csrf_token`, `check_csrf`, `SecurityHeadersMiddleware` (ASGI) and `security_headers(path, settings) -> dict`, `RateLimitRule`, `RATE_LIMITS`, `RateLimiter`, `MeteredLLM`, `ScrubResult`, `scrub`, `LimitsRepository` (rate-limit windows, LLM usage rows, monthly counts per user, prune) (ADR-0033).
- **Consumes:** `Settings`, `CsrfError`, `RateLimitedError`, `UsageLimitError`, `LLMProvider`, `LLMUsage`, `usage_sink`, `tables.py` (T-001).

## Acceptance criteria

1. CSRF: unsafe methods without the header, with a mismatching header, or from a foreign `Origin` -> `CsrfError`; GET/HEAD/OPTIONS and `/api/billing/webhook` exempt; tokens are HMACs bound to the session key and differ per session; constant-time comparison.
2. Headers: every ADR-0033 header on app responses; HSTS only in production; the website preview path gets the sandbox CSP and `frame-ancestors 'self'` instead; a test asserts the CSP has no `unsafe-eval` and no inline script allowance.
3. `RateLimiter.hit` enforces every ADR-0033 class with fixed windows in `rate_limits`; the error carries `retry_after_s` and a friendly message with minutes; disabled limiter never blocks; windows work across two `RateLimiter` instances on the same database (multi-process stand-in); prune removes old windows.
4. `MeteredLLM`: below the limit passes through and records one `llm_usage` row per call with tokens from the inner provider's reported usage; at the limit raises `UsageLimitError` with the plan name and reset date **before** calling the inner provider; counts reset at the UTC month boundary (injected clock); `user_id=None` (system jobs) is metered against the case's billing user when given, else unlimited but recorded.
5. `scrub`: removes SSNs (`123-45-6789`, `123 45 6789`, nine digits next to "SSN"/"social"), ITINs (9xx-7x/8x-xxxx), EINs (`12-3456789` next to "EIN"/"tax id"), Luhn-valid card numbers; keeps dates, phone numbers, share counts and money amounts (table-driven tests with at least 25 positive and 25 negative cases); returns the redaction kinds.
6. Nothing in this package logs a token, cookie, password or the unscrubbed text.

## Feature run (`evidence/T-032/feature_run.py`)

Prints the security headers for an app page and for a preview page; runs CSRF checks for
a valid request, a missing header and a foreign origin; hits the `auth` limit for one
email until it trips and prints the friendly message and retry-after; meters a FakeLLM
for a Free-plan user with a limit of 3 and shows the fourth call rejected without
reaching the provider; scrubs five sample chat messages and prints before/after with the
redaction kinds.

## Out of scope

Wiring the middleware and limits into the app and routes (T-016, T-039, T-041), the PII notice in the chat (T-014).
