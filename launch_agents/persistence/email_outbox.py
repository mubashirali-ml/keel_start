"""The email outbox (ADR-0029). Owned by T-028."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.engine import Engine

from ..domain.email import EmailMessage, EmailTemplate

__all__ = ["EmailOutboxRepository", "OutboxEmail"]


class OutboxEmail(BaseModel):
    """One ``email_outbox`` row."""

    id: str
    to_email: str
    template: EmailTemplate
    subject: str
    text_body: str
    html_body: str
    status: str  # queued | sent | failed
    attempts: int
    user_id: str | None = None
    case_id: str | None = None
    dedupe_key: str | None = None
    provider_id: str | None = None
    error: str | None = None
    created_at: datetime
    sent_at: datetime | None = None


class EmailOutboxRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(
        self, message: EmailMessage, *, user_id: str | None, case_id: str | None, dedupe_key: str | None
    ) -> str | None:
        """Store a queued email; None when ``dedupe_key`` already exists."""
        raise NotImplementedError("EmailOutboxRepository.add is implemented in T-028")

    def get(self, outbox_id: str) -> OutboxEmail:
        raise NotImplementedError("EmailOutboxRepository.get is implemented in T-028")

    def mark_sent(self, outbox_id: str, provider_id: str | None, *, now: datetime) -> None:
        raise NotImplementedError("EmailOutboxRepository.mark_sent is implemented in T-028")

    def mark_failed(self, outbox_id: str, error: str, *, now: datetime) -> None:
        raise NotImplementedError("EmailOutboxRepository.mark_failed is implemented in T-028")

    def list_recent(self, *, status: str | None = None, limit: int = 100) -> list[OutboxEmail]:
        raise NotImplementedError("EmailOutboxRepository.list_recent is implemented in T-028")
