# ADR-0028: Background jobs: queue, worker and scheduler

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (types, `JobRunner` port, `InlineJobRunner`), T-030 (DB runner, worker, scheduler, CLI), T-013, T-028, T-035 (handlers), T-041 (job routes), T-038 (admin retry) |
| **Scope** | `launch_agents/domain/jobs.py`, `launch_agents/ports/jobs.py`, `launch_agents/jobs/`, `persistence/jobs.py` |

## Context

The brief: long-running agent work (website build, deploy) runs as tracked jobs with
status and retry, never as a hung request; emails go out reliably; 83(b) reminders go
out at 14, 7 and 2 days. We want this without adding a broker (Redis, RabbitMQ) to a
v1 that already needs PostgreSQL.

## Decision

### Contracts (T-001)

```python
class JobStatus(str, Enum):
    QUEUED = "queued"; RUNNING = "running"; SUCCEEDED = "succeeded"; FAILED = "failed"; CANCELLED = "cancelled"
class JobKind:                                # string constants
    WEBSITE_BUILD = "website.build"; WEBSITE_DEPLOY = "website.deploy"
    EMAIL_SEND = "email.send"; REMINDERS_SWEEP = "reminders.sweep"
class JobRecord(BaseModel):
    id: str; kind: str; status: JobStatus
    case_id: str | None = None; user_id: str | None = None
    payload: dict[str, Any] = {}; result: dict[str, Any] | None = None
    error: str | None = None                  # friendly, founder-facing
    attempts: int = 0; max_attempts: int = 3
    run_at: datetime; created_at: datetime; updated_at: datetime; finished_at: datetime | None = None
@dataclass(frozen=True)
class JobContext: job: JobRecord; attempt: int; now: datetime
JobHandler = Callable[[JobRecord, JobContext], dict[str, Any] | None]
class RetryableJobError(LaunchError): code = "job_retry"; http_status = 503   # transient: try again later
class JobRegistry:
    def register(self, kind: str, handler: JobHandler) -> None
    def handler(self, kind: str) -> JobHandler                      # KeyError -> job fails "unknown job kind"
class JobRunner(Protocol):
    def enqueue(self, kind: str, payload: dict[str, Any], *, case_id: str | None = None,
                user_id: str | None = None, run_at: datetime | None = None,
                max_attempts: int = 3, dedupe_key: str | None = None) -> JobRecord
    def get(self, job_id: str) -> JobRecord                          # NotFoundError
    def list_for_case(self, case_id: str, *, limit: int = 20) -> list[JobRecord]
    def retry(self, job_id: str) -> JobRecord                        # FAILED -> QUEUED, attempts reset (admin)
class InlineJobRunner:   # implements JobRunner in memory; runs the handler synchronously inside enqueue
                         # (retrying immediately up to max_attempts, no sleeping); for tests and recorded runs
```

`dedupe_key`: enqueuing a key that already exists returns the existing job (used for
reminders and emails). Handlers must be idempotent: a job may run again after a crash.
Payloads hold ids and small values only, never secrets or document bodies.

### Database runner and worker (T-030)

```python
class DbJobRunner:      # JobRunner on the jobs table
    def __init__(self, jobs: JobsRepository, *, clock=utcnow) -> None
class Worker:
    def __init__(self, jobs: JobsRepository, registry: JobRegistry, *, worker_id: str,
                 clock=utcnow, lease_s: float = 300, poll_interval_s: float = 1.0) -> None
    def run_once(self) -> bool            # claim + run one due job; False when none was due
    def run_forever(self, stop: threading.Event) -> None
class Scheduler:        # periodic jobs, enqueued with a dedupe key per period
    def __init__(self, runner: JobRunner, *, clock=utcnow) -> None
    def tick(self) -> list[JobRecord]     # enqueues reminders.sweep once per UTC day (key "reminders.sweep:YYYY-MM-DD")
def start_embedded_worker(services: "Services") -> threading.Thread   # daemon thread, development and demo
# CLI: python -m launch_agents.jobs worker [--once]
```

- **Claiming:** PostgreSQL uses `SELECT ... FOR UPDATE SKIP LOCKED`; SQLite uses a
  conditional `UPDATE ... WHERE status='queued' AND id=?` (single worker in dev). A claim
  sets `status=running`, `locked_by`, `locked_until = now + lease_s`, `attempts += 1`.
- **Outcome:** handler returns -> `succeeded` with `result`. `RetryableJobError` or
  `is_transient` (ADR-0023) -> `queued` again with `run_at = now + 10 s * 3**(attempts-1)`
  (max 10 min) until `max_attempts`, then `failed`. Any other exception -> `failed` at
  once. `error` is always a friendly message; the technical detail is logged with the
  job id. An expired lease (crashed worker) puts the job back to `queued`.
- The worker writes `worker_heartbeats` every 30 s; readiness (ADR-0034) reports a
  stale heartbeat in production.
- Development, tests and the demo run an **embedded worker thread** inside the API
  process (`JOBS_EMBEDDED_WORKER=1`); production runs `python -m launch_agents.jobs worker`
  as its own container.

### Who uses it

| Kind | Enqueued by | Handler (ticket) |
|---|---|---|
| `website.build` | `WebsiteService.request_build` | `WebsiteService.run_build` (T-013) |
| `website.deploy` | `WebsiteService.request_deploy` | `WebsiteService.run_deploy` (T-013) |
| `email.send` | `OutboxMailer.send` | `send_outbox_email` (T-028) |
| `reminders.sweep` | `Scheduler.tick` | `ReminderSweep.run` (T-035) |

Handlers are registered in `composition.build_services` (T-016). The API exposes job
status scoped to company access (ADR-0032); the UI polls it every 1.5 s while a job runs.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. DB-backed queue + small worker (chosen) | No broker; jobs visible in admin; works on SQLite and Postgres | Polling; fine for v1 volumes |
| B. Celery / RQ + Redis | Mature | Extra service and dependency to run and secure |
| C. FastAPI `BackgroundTasks` | Built in | Lost on restart; no retry or status |

## Consequences

- A website build survives an API restart and shows progress; a failed deploy can be
  retried from the admin area.
- Tests stay synchronous and deterministic with `InlineJobRunner`.
