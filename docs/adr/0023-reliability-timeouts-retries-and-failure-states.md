# ADR-0023: Reliability: timeouts, retries and failure states

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (helper), T-007, T-008, T-024, T-025, T-028, T-029, T-030 (apply it), T-011 + wave 4 (UI states) |
| **Scope** | `launch_agents/reliability.py`, every adapter and provider, API request budgets, frontend error states |

## Context

The brief ("Reliability"): every LLM and external call has a timeout, retries on
transient errors, and a friendly error state in the UI; nothing hangs and no raw error
reaches a user. Without one policy each adapter would pick its own numbers, and a slow
registry or LLM would hang a chat request.

## Decision

### Shared helper (`launch_agents/reliability.py`, implemented in T-001, pure)

```python
@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3                 # total tries, including the first
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter: bool = True               # +-20 %, disabled in tests
    retry_on: Callable[[BaseException], bool] = is_transient
def is_transient(exc: BaseException) -> bool       # httpx timeouts/connect errors, HTTP 408/425/429/5xx, RetryableError
class RetryableError(LaunchError): code = "temporarily_unavailable"; http_status = 503
def call_with_retry(fn: Callable[[], T], policy: RetryPolicy, *, sleep: Callable[[float], None] = time.sleep,
                    on_retry: Callable[[int, BaseException], None] | None = None) -> T
class Deadline:                                     # overall budget across several calls
    def __init__(self, seconds: float, *, clock: Callable[[], float] = time.monotonic): ...
    def remaining(self) -> float; def expired(self) -> bool
```

Backoff is exponential (`base * 2**(n-1)`, capped). `Retry-After` from an HTTP 429/503
is honoured when shorter than `max_delay_s`. Tests pass a no-op `sleep`.

### Budgets per call

| Call | Timeout | Retries | When it still fails |
|---|---|---|---|
| Anthropic SDK | `LLM_TIMEOUT_S` 60 s | SDK `max_retries=2`; +1 on invalid JSON | `LLMOutputError` -> agent apologises (ADR-0009) |
| claude_code CLI | 120 s | 1 on non-zero exit / `is_error`, none on timeout | `LLMOutputError` |
| DeepSeek / Groq | 60 s | 2 (client) | `LLMOutputError` |
| RDAP lookup | 5 s each, 12 s per name check overall (`Deadline`), lookups in a 6-thread pool | 1 on connect error / 5xx; never on 404 / 429 | that domain is `unknown`, never `available` |
| Netlify API | 30 s per request, deploy poll <= 60 s | 2 on 429 / 5xx | `DeployResult(status="failed")` with a friendly message (ADR-0011: never raises); the founder can retry the deploy |
| Stripe SDK | 20 s | SDK `max_network_retries=2` | `PaymentProviderError` (502) "Payments are unavailable right now. Please try again in a minute." |
| SMTP | 10 s | outbox job: 5 attempts with backoff | email row `failed`; admin sees it (ADR-0034) |
| Database | `pool_pre_ping`; Postgres `statement_timeout` 15 s | none | 503 `temporarily_unavailable` |

### Request budgets

- No HTTP request does long work. Website build and deploy, emails and reminder sweeps
  run as tracked jobs (ADR-0028); the request returns the job at once.
- A chat turn makes at most four LLM calls (Manager extract + route, one specialist,
  plus its JSON retry) and must answer within 90 s; the API enforces a 100 s hard
  timeout and returns a friendly 503 instead of hanging.
- Every other endpoint is expected to answer within 5 s.

### Failure states the founder sees

- Every `LaunchError` carries friendly English (ADR-0008). Unknown exceptions become
  500 `internal` with "Something went wrong on our side. Please try again." and a
  `request_id` the founder can quote (ADR-0034).
- Frontend (T-011 client, every screen): `fetch` with a timeout (chat 100 s, others
  20 s); GET queries retry twice on network errors; mutations never auto-retry; every
  view has loading, empty and error states, and every error state offers a recovery
  action (Retry, Go back, Contact support).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. One helper + a budget table + jobs for long work (chosen) | Predictable; testable without sleeping; nothing hangs | Each adapter must use it (the reviewer checks) |
| B. A retry library (tenacity) | Feature-rich | New dependency for ~40 lines of code |
| C. Per-adapter ad-hoc retries | No coordination | Inconsistent; easy to forget timeouts |

## Consequences

- Reviewers check every outbound call for an explicit timeout and the policy above.
- A slow registry or LLM degrades to "couldn't check" or an apology, never a hang.
