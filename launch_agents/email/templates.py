"""Transactional email templates (ADR-0029, branding ADR-0039). Owned by T-028.

``TEMPLATE_DATA_KEYS`` is the ADR-0029 data-key table; ``render_email`` is implemented by T-028
with ``string.Template`` and ``html.escape`` (no remote images, no sensitive data).
"""

from __future__ import annotations

from typing import Any, Mapping

from ..domain.email import EmailMessage, EmailTemplate

__all__ = ["TEMPLATE_DATA_KEYS", "render_email"]

TEMPLATE_DATA_KEYS: Mapping[EmailTemplate, frozenset[str]] = {
    EmailTemplate.VERIFY_EMAIL: frozenset({"full_name", "link"}),
    EmailTemplate.PASSWORD_RESET: frozenset({"full_name", "link"}),
    EmailTemplate.INVITE_COFOUNDER: frozenset({"inviter_name", "company_name", "founder_name", "link"}),
    EmailTemplate.SIGNATURE_NEEDED: frozenset({"founder_name", "company_name", "document_title", "version", "link"}),
    EmailTemplate.DOCUMENT_EXECUTED: frozenset({"founder_name", "company_name", "document_title", "link"}),
    EmailTemplate.DEADLINE_83B_REMINDER: frozenset({"founder_name", "company_name", "deadline", "days_left", "link"}),
}


def render_email(template: EmailTemplate, data: Mapping[str, Any], *, brand_name: str, base_url: str) -> EmailMessage:
    """Subject with the brand prefix, plain-text and HTML parts; missing keys raise ``KeyError`` (T-028)."""
    raise NotImplementedError("render_email is implemented in T-028")
