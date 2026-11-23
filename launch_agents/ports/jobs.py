"""Job runner port, handler registry and the in-memory inline runner (ADR-0028).

The database runner, worker and scheduler are ``jobs/`` (T-030). ``InlineJobRunner`` runs the
handler synchronously inside ``enqueue``, retrying immediately (no sleeping) up to
``max_attempts``: tests and recorded runs stay deterministic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Protocol, runtime_checkable

from ..domain.errors import InvalidStateError, LaunchError, NotFoundError
from ..domain.helpers import new_id, utcnow
from ..domain.jobs import JobContext, JobHandler, JobRecord, JobStatus, RetryableJobError
from ..reliability import is_transient

__all__ = [
    "GENERIC_JOB_ERROR",
    "UNKNOWN_JOB_KIND_ERROR",
    "InlineJobRunner",
    "JobRegistry",
    "JobRunner",
]

log = logging.getLogger(__name__)

UNKNOWN_JOB_KIND_ERROR = "This task type is not available."
GENERIC_JOB_ERROR = "This task couldn't be completed. Please try again."


class JobRegistry:
    """Maps a job kind to its handler (registered by the composition root, T-016)."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, kind: str, handler: JobHandler) -> None:
        self._handlers[kind] = handler

    def handler(self, kind: str) -> JobHandler:
        """The handler for ``kind``; ``KeyError`` when none is registered (the job then fails)."""
        try:
            return self._handlers[kind]
        except KeyError:
            raise KeyError(kind) from None

    def kinds(self) -> list[str]:
        return sorted(self._handlers)

    def __contains__(self, kind: object) -> bool:
        return kind in self._handlers


@runtime_checkable
class JobRunner(Protocol):
    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        case_id: str | None = None,
        user_id: str | None = None,
        run_at: datetime | None = None,
        max_attempts: int = 3,
        dedupe_key: str | None = None,
    ) -> JobRecord:
        """Store (or, for an existing ``dedupe_key``, return the existing) job."""
        ...

    def get(self, job_id: str) -> JobRecord:
        """The job; ``NotFoundError`` for an unknown id."""
        ...

    def list_for_case(self, case_id: str, *, limit: int = 20) -> list[JobRecord]:
        """The company's jobs, newest first."""
        ...

    def retry(self, job_id: str) -> JobRecord:
        """FAILED -> QUEUED with attempts reset (admin)."""
        ...


def _friendly_error(exc: BaseException) -> str:
    if isinstance(exc, LaunchError) and not isinstance(exc, RetryableJobError):
        return exc.message
    return GENERIC_JOB_ERROR


class InlineJobRunner:
    """``JobRunner`` in memory that runs each job at once, for tests and recorded runs."""

    def __init__(self, registry: JobRegistry | None = None, *, clock: Callable[[], datetime] = utcnow) -> None:
        self.registry = registry if registry is not None else JobRegistry()
        self.clock = clock
        self.jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._dedupe: dict[str, str] = {}

    def register(self, kind: str, handler: JobHandler) -> None:
        """Shortcut for ``runner.registry.register``."""
        self.registry.register(kind, handler)

    def _save(self, job: JobRecord, **changes: Any) -> JobRecord:
        updated = job.model_copy(update={**changes, "updated_at": self.clock()})
        self.jobs[updated.id] = updated
        return updated

    def _run(self, job: JobRecord) -> JobRecord:
        try:
            handler = self.registry.handler(job.kind)
        except KeyError:
            log.warning("job %s failed: no handler for kind %r", job.id, job.kind)
            now = self.clock()
            return self._save(job, status=JobStatus.FAILED, error=UNKNOWN_JOB_KIND_ERROR, finished_at=now)
        while True:
            now = self.clock()
            job = self._save(job, status=JobStatus.RUNNING, attempts=job.attempts + 1)
            try:
                result = handler(job, JobContext(job=job, attempt=job.attempts, now=now))
            except Exception as exc:  # the job records the outcome; nothing escapes enqueue
                retryable = isinstance(exc, RetryableJobError) or is_transient(exc)
                if retryable and job.attempts < job.max_attempts:
                    log.info("job %s attempt %d failed transiently: %s", job.id, job.attempts, exc)
                    job = self._save(job, status=JobStatus.QUEUED)
                    continue
                log.warning("job %s (%s) failed after %d attempt(s): %r", job.id, job.kind, job.attempts, exc)
                return self._save(job, status=JobStatus.FAILED, error=_friendly_error(exc), finished_at=self.clock())
            return self._save(
                job, status=JobStatus.SUCCEEDED, result=result, error=None, finished_at=self.clock()
            )

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        case_id: str | None = None,
        user_id: str | None = None,
        run_at: datetime | None = None,
        max_attempts: int = 3,
        dedupe_key: str | None = None,
    ) -> JobRecord:
        if dedupe_key is not None and dedupe_key in self._dedupe:
            return self.jobs[self._dedupe[dedupe_key]]
        now = self.clock()
        job = JobRecord(
            id=new_id("job"),
            kind=kind,
            status=JobStatus.QUEUED,
            case_id=case_id,
            user_id=user_id,
            payload=dict(payload),
            max_attempts=max(1, max_attempts),
            run_at=run_at or now,
            created_at=now,
            updated_at=now,
        )
        self.jobs[job.id] = job
        self._order.append(job.id)
        if dedupe_key is not None:
            self._dedupe[dedupe_key] = job.id
        return self._run(job)

    def get(self, job_id: str) -> JobRecord:
        job = self.jobs.get(job_id)
        if job is None:
            raise NotFoundError("We couldn't find that task.", details={"job_id": job_id})
        return job

    def list_for_case(self, case_id: str, *, limit: int = 20) -> list[JobRecord]:
        jobs = [self.jobs[i] for i in reversed(self._order) if self.jobs[i].case_id == case_id]
        return jobs[:limit]

    def retry(self, job_id: str) -> JobRecord:
        job = self.get(job_id)
        if job.status != JobStatus.FAILED:
            raise InvalidStateError("Only a failed task can be retried.", details={"status": job.status.value})
        job = self._save(job, status=JobStatus.QUEUED, attempts=0, error=None, result=None, finished_at=None)
        return self._run(job)
