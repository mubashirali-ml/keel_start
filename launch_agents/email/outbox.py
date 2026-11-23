"""Outbox delivery: never lost, never sent twice (ADR-0029). Owned by T-028."""

from __future__ import annotations

from typing import Any, Mapping

from ..config import Settings
from ..domain.email import EmailTemplate
from ..domain.jobs import JobContext, JobRecord
from ..persistence.email_outbox import EmailOutboxRepository
from ..ports.email import EmailSender
from ..ports.jobs import JobRunner

__all__ = ["OutboxMailer", "send_outbox_email"]


class OutboxMailer:
    """``Mailer``: renders, stores the outbox row (deduplicated) and enqueues ``email.send``."""

    def __init__(self, outbox: EmailOutboxRepository, jobs: JobRunner, settings: Settings) -> None:
        self.outbox = outbox
        self.jobs = jobs
        self.settings = settings

    def send(
        self,
        template: EmailTemplate,
        to: str,
        data: Mapping[str, Any],
        *,
        user_id: str | None = None,
        case_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> str | None:
        raise NotImplementedError("OutboxMailer.send is implemented in T-028")


def send_outbox_email(
    job: JobRecord, ctx: JobContext, *, outbox: EmailOutboxRepository, sender: EmailSender
) -> dict:
    """The ``email.send`` job handler: transient failure -> ``RetryableJobError``; permanent ->
    row ``failed`` (T-028)."""
    raise NotImplementedError("send_outbox_email is implemented in T-028")
