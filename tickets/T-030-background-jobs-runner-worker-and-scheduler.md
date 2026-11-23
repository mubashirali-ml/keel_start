# T-030: Background jobs: database queue, worker with retries, scheduler and CLI

| | |
|---|---|
| **Wave** | 1 |
| **Depends on** | T-001 |
| **ADRs** | [ADR-0028](../docs/adr/0028-background-jobs-queue-worker-and-scheduler.md), [ADR-0023](../docs/adr/0023-reliability-timeouts-retries-and-failure-states.md), [ADR-0027](../docs/adr/0027-persistence-v2-postgresql-sqlite-migrations-and-data-model.md), [ADR-0034](../docs/adr/0034-deployment-operations-privacy-and-admin.md) |
| **Status** | todo |

## Goal

Long-running work (website build and deploy, emails, the daily 83(b) reminder sweep) runs
as tracked jobs with status, automatic retry with backoff and recovery after a crash,
in a worker that runs inside the app in development and as its own process in production.

## Owns (only these paths may change)

- `launch_agents/jobs/`
- `launch_agents/persistence/jobs.py`
- `tests/test_jobs.py`
- `evidence/T-030/`
- `prs/T-030.md`

## Contracts

- **Provides:** `DbJobRunner` (implements `JobRunner`), `Worker`, `Scheduler`, `start_embedded_worker`, `JobsRepository`, CLI `python -m launch_agents.jobs worker [--once]` (ADR-0028).
- **Consumes:** `JobRecord`, `JobStatus`, `JobKind`, `JobContext`, `JobRegistry`, `RetryableJobError`, `is_transient`, `tables.py`, `Settings` (T-001). `start_embedded_worker` takes the `Services` dataclass (T-001) and uses only its `settings`, `engine`, `job_registry` fields.

## Acceptance criteria

1. `enqueue` stores a `queued` job; `dedupe_key` returns the existing job; `get`, `list_for_case` (newest first) and `retry` (FAILED -> QUEUED, attempts reset) behave per ADR-0028.
2. `Worker.run_once` claims the oldest due job, sets `running`, lease and attempts, runs the handler with a `JobContext`, stores `succeeded` + result; returns False when nothing is due; future `run_at` jobs are not claimed early.
3. Retries: `RetryableJobError` or a transient exception re-queues with `run_at = now + 10 s * 3**(attempts-1)` (capped at 10 min) until `max_attempts`, then `failed`; any other exception -> `failed` at once; `error` is friendly and the traceback is only logged.
4. An expired lease (simulated crashed worker) returns the job to `queued`, and it runs once more; handlers registered as idempotent are not double-applied in the test scenario.
5. Two workers on PostgreSQL (`SKIP LOCKED`, test marked `postgres`) never run the same job; on SQLite the conditional update prevents a double claim.
6. Heartbeats written every 30 s (injected clock); `Scheduler.tick` enqueues `reminders.sweep` once per UTC day (dedupe key) and is safe to call every minute.
7. `start_embedded_worker` runs a daemon thread that stops on an event; the CLI runs the worker loop with `--once` support and clean shutdown on Ctrl+C / SIGTERM.
8. Unknown job kinds fail with "This task type is not available." and do not crash the worker.

## Feature run (`evidence/T-030/feature_run.py`)

On a temp SQLite database with an injected clock and a registry of demo handlers:
enqueues a succeeding job, a job that fails twice transiently then succeeds, a job that
always fails, and a deduplicated job; runs `run_once` repeatedly while advancing the
clock and prints each job's status, attempts and `run_at` after every step; simulates a
crashed lease and its recovery; runs `Scheduler.tick` twice on the same day and once the
next day and prints the sweep jobs; prints the heartbeat row.

## Out of scope

The handlers themselves (T-013, T-028, T-035), job routes (T-041), admin retry UI (T-045), the worker container (T-034).
