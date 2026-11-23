"""Transactional email types (ADR-0029). Ports and fakes are in ``ports/email.py``."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

__all__ = ["EmailMessage", "EmailTemplate", "SendResult"]


class EmailTemplate(str, Enum):
    VERIFY_EMAIL = "verify_email"
    PASSWORD_RESET = "password_reset"
    INVITE_COFOUNDER = "invite_cofounder"
    SIGNATURE_NEEDED = "signature_needed"
    DOCUMENT_EXECUTED = "document_executed"
    DEADLINE_83B_REMINDER = "deadline_83b_reminder"


class EmailMessage(BaseModel):
    to: str
    subject: str
    text: str
    html: str
    template: EmailTemplate


class SendResult(BaseModel):
    ok: bool
    provider_id: str | None = None
    error: str | None = None
    transient: bool = False
