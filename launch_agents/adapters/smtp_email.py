"""SMTP email sender (ADR-0029): stdlib ``smtplib``, STARTTLS, 10 s timeout. Owned by T-028."""

from __future__ import annotations

import smtplib
from typing import Callable

from ..config import Settings
from ..domain.email import EmailMessage, SendResult

__all__ = ["SmtpEmailSender"]


class SmtpEmailSender:
    """``EmailSender`` for any SMTP provider (Postmark, SES, Resend, Mailgun, ...); never raises
    for provider errors (transient vs. permanent in ``SendResult``)."""

    name = "smtp"

    def __init__(self, settings: Settings, *, smtp_factory: Callable[..., smtplib.SMTP] | None = None) -> None:
        self.settings = settings
        self.smtp_factory = smtp_factory

    def send(self, message: EmailMessage) -> SendResult:
        raise NotImplementedError("SmtpEmailSender.send is implemented in T-028")
