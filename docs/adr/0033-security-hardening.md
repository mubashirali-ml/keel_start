# ADR-0033: Security hardening

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (contracts), T-032 (implements), T-016 (wires middleware), T-039/T-041 (apply limits), T-011 (CSRF in the client, no inline scripts) |
| **Scope** | `launch_agents/security/`, `persistence/limits.py`, API middleware, frontend client |

## Context

The brief ("Security"): input validation everywhere, rate limiting on auth and LLM
endpoints, CORS locked to the app's origin, security headers, CSRF protection for cookie
auth, per-account LLM usage limits, and sensitive personal data (SSN, address) never
stored. Founders will trust the product with company documents and signatures.

## Decision

### Cookies and CSRF (`security/csrf.py`)

- Session cookie `la_session`: `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when
  `APP_ENV=production` (or `APP_BASE_URL` is https), max-age = session expiry.
- CSRF: double-submit token. Cookie `la_csrf` (readable by JS, `SameSite=Strict`,
  `Secure` in production) holds `HMAC(SECRET_KEY, session token hash or anonymous nonce)`.
  Every `POST/PUT/PATCH/DELETE` under `/api` must send header `X-CSRF-Token` equal to
  the cookie, and when an `Origin` header is present it must be in `cors_origins` or
  equal to `APP_BASE_URL`; else `CsrfError`. Exempt: `/api/billing/webhook` (Stripe
  signature instead). `MeView.csrf_token` and `GET /api/auth/me` refresh the token; the
  frontend client sends it automatically.

```python
def issue_csrf_token(secret: str, session_key: str) -> str
def check_csrf(method: str, path: str, header_token: str | None, cookie_token: str | None,
               origin: str | None, settings: Settings) -> None        # CsrfError
```

### Headers (`security/headers.py`) and CORS

Every response: `X-Content-Type-Options: nosniff`, `Referrer-Policy:
strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(),
geolocation=()`, `X-Frame-Options: DENY`, `Cross-Origin-Opener-Policy: same-origin`;
`Strict-Transport-Security: max-age=31536000; includeSubDomains` in production. App
pages: `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'
'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src
'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
https://checkout.stripe.com https://billing.stripe.com`. Hence **no inline scripts** in
the frontend (the theme bootstrap is a static `/theme-init.js`). The website preview
keeps `sandbox; default-src 'self'` and `frame-ancestors 'self'` (ADR-0017). CORS allows
only `cors_origins` (production: the app origin), with credentials.

### Rate limits (`security/rate_limit.py`, storage `persistence/limits.py`)

```python
class RateLimitRule(BaseModel): name: str; limit: int; window_s: int
RATE_LIMITS: Mapping[str, list[RateLimitRule]]   # classes below
class RateLimiter:
    def __init__(self, limits: LimitsRepository, *, enabled: bool, clock=utcnow) -> None
    def hit(self, cls: str, *, keys: Mapping[str, str]) -> None     # RateLimitedError(details.retry_after_s)
```

Fixed windows stored in `rate_limits` (works across processes on Postgres):

| Class | Limits |
|---|---|
| `auth` (login, signup, reset, password change) | 10 / 15 min per IP; 5 / 15 min per email |
| `email` (forgot password, resend verification) | 3 / hour per email; 10 / hour per IP |
| `llm` (chat message, name recheck, website build) | 20 / min and 300 / day per user |
| `invite` | 20 / day per user |

The response is 429 with `Retry-After` and a friendly message ("Too many attempts. Try
again in 4 minutes."). Old windows are pruned by the daily sweep.

### LLM usage limits (`security/metering.py`)

```python
class MeteredLLM:     # implements LLMProvider, wraps the real one per request/job
    def __init__(self, inner: LLMProvider, limits: LimitsRepository, *, user_id: str | None,
                 case_id: str | None, monthly_limit: int, clock=utcnow) -> None
```

Before each call: if the billing user's calls this calendar month (UTC) >=
`entitlements.llm_calls_per_month`, raise `UsageLimitError` ("You've used this month's
AI allowance on the {plan} plan. Upgrade or wait until {date}."). Agents catch only
`LLMOutputError`, so it propagates out of the turn; `CaseService.post_message` catches it,
keeps facts and state unchanged, and posts a Manager notice with that message and an
upgrade suggestion; a job hitting it fails with the same friendly message. After each call: one `llm_usage` row via the
`usage_sink` (ADR-0022) with tokens when known. The admin area shows usage per user.

### Input validation

Every request body is a pydantic model with `extra="forbid"` and limits: chat text 1–4,000
chars; names <= 120; emails validated (`email-validator`) and <= 254; document content
<= 100,000; change requests <= 2,000; passwords 10–128. Path ids match
`^[a-z]+_[0-9a-f]{12}$` or the documented form. Uploaded payloads other than the Stripe
webhook (<= 256 KB) are not accepted.

### Sensitive data (`security/pii.py`)

```python
class ScrubResult(BaseModel): text: str; redactions: list[Literal["ssn", "itin", "ein", "card"]]
def scrub(text: str) -> ScrubResult
```

Founder chat text is scrubbed **before it is stored or sent to an LLM**: US SSN / ITIN
patterns (`123-45-6789`, nine digits with SSN context words), EINs, and payment-card
numbers (Luhn-valid 13–19 digits) become `[removed: SSN]` etc. When anything was removed
the Manager adds one notice: "For your safety I removed a tax ID from your message.
Never share SSNs or tax IDs here; add them only in your downloaded documents." Documents
keep their placeholders (`[TAXPAYER ID]`, `[ADDRESS]`); there are no fields for SSNs or
home addresses anywhere in the data model. The website's public business contact
details (`contact_address`) are the only address the product stores, and the UI labels
it "shown publicly on your website".

### Secrets and logs

Secrets only from environment variables; `Settings.__repr__` and logs redact every
field whose name contains `key`, `secret`, `token` or `password`; request logs never
include bodies of `/api/auth/*`, `/api/account*` or cookies/`Authorization` headers;
emails in logs are masked (`a***@example.com`).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Own small middleware + DB-backed limits (chosen) | No new dependency; works with several app instances on Postgres | We maintain it (tests cover it) |
| B. slowapi + Redis | Mature limiter | New dependency and service |
| C. Bearer tokens instead of cookies (no CSRF needed) | Simple for APIs | Tokens readable by JS; XSS exposure |

## Consequences

- The UI must send the CSRF header and avoid inline scripts (T-011).
- A route-walking test (T-016) asserts every unsafe route is CSRF-protected and every
  `/api/auth/*` and LLM route has a rate-limit class.
