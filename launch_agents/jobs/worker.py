"""The job worker, the scheduler and the embedded worker thread (ADR-0028). Owned by T-030."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from ..domain.helpers import utcnow
from ..domain.jobs import JobRecord
from ..persistence.jobs import JobsRepository
from ..ports.jobs import JobRegistry, JobRunner

if TYPE_CHECKING:  # pragma: no cover
    from ..composition import Services

__all__ = ["Scheduler", "Worker", "start_embedded_worker"]


class Worker:
    def __init__(
        self,
        jobs: JobsRepository,
        registry: JobRegistry,
        *,
        worker_id: str,
        clock: Callable[[], datetime] = utcnow,
        lease_s: float = 300,
        poll_interval_s: float = 1.0,
    ) -> None:
        self.jobs = jobs
        self.registry = registry
        self.worker_id = worker_id
        self.clock = clock
        self.lease_s = lease_s
        self.poll_interval_s = poll_interval_s

    def run_once(self) -> bool:
        """Claim and run one due job; False when none was due."""
        raise NotImplementedError("Worker.run_once is implemented in T-030")

    def run_forever(self, stop: threading.Event) -> None:
        raise NotImplementedError("Worker.run_forever is implemented in T-030")


class Scheduler:
    """Periodic jobs, enqueued with a dedupe key per period."""

    def __init__(self, runner: JobRunner, *, clock: Callable[[], datetime] = utcnow) -> None:
        self.runner = runner
        self.clock = clock

    def tick(self) -> list[JobRecord]:
        """Enqueues ``reminders.sweep`` once per UTC day (key ``reminders.sweep:YYYY-MM-DD``)."""
        raise NotImplementedError("Scheduler.tick is implemented in T-030")


def start_embedded_worker(services: "Services") -> threading.Thread:
    """Daemon worker thread for development and the demo; uses only ``services.settings``,
    ``services.engine`` and ``services.job_registry`` (T-030)."""
    raise NotImplementedError("start_embedded_worker is implemented in T-030")
