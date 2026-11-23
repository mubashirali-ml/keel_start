"""Signature-needed / executed emails and the daily 83(b) reminder sweep (ADR-0029). Owned by T-035."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Sequence

from ..config import Settings
from ..domain.documents import Document
from ..domain.jobs import JobContext, JobRecord
from ..persistence.accounts import AccountsRepository
from ..persistence.repository import Repository
from ..persistence.team import TeamRepository
from ..ports.email import Mailer
from ..ports.jobs import JobRegistry

__all__ = ["EmailNotifier", "ReminderSweep", "register_notification_jobs"]


class EmailNotifier:
    """``Notifier`` that emails founders (dedupe ``sig:{doc}:{version}:{founder}`` and
    ``exec:{doc}:{version}:{user}``)."""

    def __init__(
        self,
        repo: Repository,
        team: TeamRepository,
        accounts: AccountsRepository,
        mailer: Mailer,
        settings: Settings,
    ) -> None:
        self.repo = repo
        self.team = team
        self.accounts = accounts
        self.mailer = mailer
        self.settings = settings

    def signatures_needed(self, case_id: str, document: Document, founder_ids: Sequence[str]) -> None:
        raise NotImplementedError("EmailNotifier.signatures_needed is implemented in T-035")

    def document_executed(self, case_id: str, document: Document) -> None:
        raise NotImplementedError("EmailNotifier.document_executed is implemented in T-035")


class ReminderSweep:
    """83(b) reminders at 14, 7 and 2 days: only the smallest due threshold, never after the deadline."""

    THRESHOLDS = (14, 7, 2)

    def __init__(
        self,
        repo: Repository,
        team: TeamRepository,
        accounts: AccountsRepository,
        mailer: Mailer,
        *,
        today: Callable[[], date],
    ) -> None:
        self.repo = repo
        self.team = team
        self.accounts = accounts
        self.mailer = mailer
        self.today = today

    def run(self, job: JobRecord | None = None, ctx: JobContext | None = None) -> dict[str, Any]:
        """The ``reminders.sweep`` handler (T-035)."""
        raise NotImplementedError("ReminderSweep.run is implemented in T-035")


def register_notification_jobs(registry: JobRegistry, sweep: ReminderSweep) -> None:
    """Register the ``reminders.sweep`` handler (T-035)."""
    raise NotImplementedError("register_notification_jobs is implemented in T-035")
