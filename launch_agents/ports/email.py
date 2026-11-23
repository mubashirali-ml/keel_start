"""Email ports and fakes (ADR-0029).

``EmailSender`` is the transport (SMTP, console, file drop, fake); ``Mailer`` is what
services call (the outbox implementation is ``email/outbox.py``, T-028).
"""

from __future__ import annotations

from typing import Any, Mapping, NamedTuple, Protocol, runtime_checkable

from ..domain.email import EmailMessage, EmailTemplate, SendResult

__all__ = ["EmailSender", "FakeEmailSender", "Mailer", "RecordingMailer", "SentEmail"]


@runtime_checkable
class EmailSender(Protocol):
    name: str

    def send(self, message: EmailMessage) -> SendResult:
        """Send one message; never raises for provider errors (``ok=False``, ``transient``)."""
        ...


class FakeEmailSender:
    """Test transport: records sent messages in ``.sent``; ``fail_next(n, transient=True)``
    makes the next ``n`` sends fail."""

    name = "fake"

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self._failures: list[bool] = []

    def fail_next(self, n: int = 1, *, transient: bool = True) -> None:
        self._failures.extend([transient] * n)

    def send(self, message: EmailMessage) -> SendResult:
        if self._failures:
            transient = self._failures.pop(0)
            return SendResult(
                ok=False,
                error="the email provider is temporarily unavailable" if transient else "the email provider rejected the message",
                transient=transient,
            )
        self.sent.append(message)
        return SendResult(ok=True, provider_id=f"fake-{len(self.sent)}")


@runtime_checkable
class Mailer(Protocol):
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
        """Queue an email; returns the outbox id, or None when deduplicated."""
        ...


class SentEmail(NamedTuple):
    template: EmailTemplate
    to: str
    data: Mapping[str, Any]
    dedupe_key: str | None


class RecordingMailer:
    """Fake ``Mailer``: ``.sent`` lists ``(template, to, data, dedupe_key)``; honours ``dedupe_key``."""

    def __init__(self) -> None:
        self.sent: list[SentEmail] = []
        self.meta: list[dict[str, str | None]] = []  # user_id / case_id per sent entry, same order
        self._keys: set[str] = set()

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
        if dedupe_key is not None:
            if dedupe_key in self._keys:
                return None
            self._keys.add(dedupe_key)
        self.sent.append(SentEmail(template, to, dict(data), dedupe_key))
        self.meta.append({"user_id": user_id, "case_id": case_id})
        return f"outbox_{len(self.sent):06d}"

    def to(self, address: str) -> list[SentEmail]:
        """Every recorded email to ``address`` (case-insensitive)."""
        return [e for e in self.sent if e.to.lower() == address.lower()]
