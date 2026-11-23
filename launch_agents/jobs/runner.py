"""The database job runner (ADR-0028). Owned by T-030."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from ..domain.helpers import utcnow
from ..domain.jobs import JobRecord
from ..persistence.jobs import JobsRepository

__all__ = ["DbJobRunner"]


class DbJobRunner:
    """``JobRunner`` on the ``jobs`` table; a ``Worker`` executes the queued jobs."""

    def __init__(self, jobs: JobsRepository, *, clock: Callable[[], datetime] = utcnow) -> None:
        self.jobs = jobs
        self.clock = clock

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
        raise NotImplementedError("DbJobRunner.enqueue is implemented in T-030")

    def get(self, job_id: str) -> JobRecord:
        raise NotImplementedError("DbJobRunner.get is implemented in T-030")

    def list_for_case(self, case_id: str, *, limit: int = 20) -> list[JobRecord]:
        raise NotImplementedError("DbJobRunner.list_for_case is implemented in T-030")

    def retry(self, job_id: str) -> JobRecord:
        raise NotImplementedError("DbJobRunner.retry is implemented in T-030")
