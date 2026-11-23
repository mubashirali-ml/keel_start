# T-033: Observability: structured logs, request ids, redaction and pluggable error reporting

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md), [ADR-0033](../docs/adr/0033-security-hardening.md), [ADR-0021](../docs/adr/0021-settings-environments-and-production-guards.md) |
| **Status** | todo |

## Goal

When something goes wrong in production, the owner can find it: every request and job
writes structured log lines with a request id, secrets and personal data are redacted
from logs, and unexpected errors go to a pluggable error reporter while the founder sees
a friendly message with a reference number.

## Owns (only these paths may change)

- `launch_agents/observability/`
- `tests/test_observability.py`
- `evidence/T-033/`
- `prs/T-033.md`

## Contracts

- **Provides:** `configure_logging(settings)`, `RequestContextMiddleware`, `log_context(**fields)`, `current_request_id()`, `RedactingFilter`, `ErrorReporter`, `load_error_reporter(dotted)`, `report_error(exc, **context)` (ADR-0034).
- **Consumes:** `Settings` (`log_format`, `log_level`, `error_reporter`) (T-001). Standard library `logging`, `contextvars`, `json`.

## Acceptance criteria

1. JSON format: one object per line with `ts` (ISO UTC), `level`, `logger`, `msg`, and `request_id`, `user_id`, `case_id`, `job_id` when bound; text format for development; level from settings.
2. `RequestContextMiddleware` accepts a valid incoming `X-Request-ID` (`[A-Za-z0-9-]{8,64}`) or generates one, returns it in the response header, binds it for the request, and logs one access line (method, route template, status, duration_ms) per request without query strings that contain `token`.
3. `RedactingFilter` masks values of keys containing `key`, `secret`, `token`, `password`, `authorization`, `cookie`; masks emails to `a***@example.com`; leaves other text alone (table-driven tests).
4. `load_error_reporter("pkg.mod:func")` loads a callable; a bad path raises `ConfigError` at startup; `report_error` calls it with the exception and context (request id, route, user id, job id), never raises even if the reporter raises, and logs at ERROR.
5. Context binding is per request/thread (two concurrent requests in a test keep their own ids) and `log_context` nests.
6. Overhead per request under 1 ms in a micro-benchmark test (no assertion flakiness: median of 200 runs).

## Feature run (`evidence/T-033/feature_run.py`)

Mounts the middleware on a tiny FastAPI app with `TestClient`: sends one request with
and one without `X-Request-ID` and prints the response headers and the captured JSON log
lines; logs a message containing an API key, a password and an email and prints the
redacted line; raises an exception in a route with a custom reporter installed and prints
what the reporter received.

## Out of scope

Wiring into the real app and jobs (T-016, T-030), health/readiness routes (T-016), CI and Docker (T-034).
