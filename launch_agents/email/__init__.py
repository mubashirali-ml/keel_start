"""Transactional email: templates, outbox and senders (ADR-0029). Owned by T-028."""

from .outbox import OutboxMailer, send_outbox_email
from .senders import ConsoleEmailSender, FileDropEmailSender
from .templates import TEMPLATE_DATA_KEYS, render_email

__all__ = [
    "ConsoleEmailSender",
    "FileDropEmailSender",
    "OutboxMailer",
    "TEMPLATE_DATA_KEYS",
    "render_email",
    "send_outbox_email",
]
