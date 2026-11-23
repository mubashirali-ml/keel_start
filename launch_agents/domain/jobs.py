"""Background job types (ADR-0028). The runner port is ``ports/jobs.py``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel

from .errors import LaunchError

__all__ = ["JobContext", "JobHandler", "JobKind", "JobRecord", "JobStatus", "RetryableJobError"]


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind:
    """Job kind string constants."""

    WEBSITE_BUILD = "website.build"
    WEBSITE_DEPLOY = "website.deploy"
    EMAIL_SEND = "email.send"
    REMINDERS_SWEEP = "reminders.sweep"


class JobRecord(BaseModel):
    id: str
    kind: str
    status: JobStatus
    case_id: str | None = None
    user_id: str | None = None
    payload: dict[str, Any] = {}  # ids and small values only; never secrets or document bodies
    result: dict[str, Any] | None = None
    error: str | None = None  # friendly, founder-facing
    attempts: int = 0
    max_attempts: int = 3
    run_at: datetime
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


@dataclass(frozen=True)
class JobContext:
    job: JobRecord
    attempt: int
    now: datetime


JobHandler = Callable[[JobRecord, JobContext], "dict[str, Any] | None"]


class RetryableJobError(LaunchError):
    """Transient: the job should be tried again later (ADR-0028)."""

    code = "job_retry"
    http_status = 503
