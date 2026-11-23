"""Notifier port and fake (ADR-0029). The email implementation is ``notifications/`` (T-035)."""

from __future__ import annotations

from typing import NamedTuple, Protocol, Sequence, runtime_checkable

from ..domain.documents import Document

__all__ = ["NotificationEvent", "Notifier", "RecordingNotifier"]


@runtime_checkable
class Notifier(Protocol):
    """What ``LegalService`` calls after drafting, editing, regenerating and executing documents."""

    def signatures_needed(self, case_id: str, document: Document, founder_ids: Sequence[str]) -> None: ...

    def document_executed(self, case_id: str, document: Document) -> None: ...


class NotificationEvent(NamedTuple):
    kind: str  # "signatures_needed" | "document_executed"
    case_id: str
    document_id: str
    version: int
    founder_ids: tuple[str, ...]


class RecordingNotifier:
    """Fake ``Notifier``: ``.events`` lists every call in order."""

    def __init__(self) -> None:
        self.events: list[NotificationEvent] = []

    def signatures_needed(self, case_id: str, document: Document, founder_ids: Sequence[str]) -> None:
        self.events.append(
            NotificationEvent("signatures_needed", case_id, document.id, document.version, tuple(founder_ids))
        )

    def document_executed(self, case_id: str, document: Document) -> None:
        self.events.append(NotificationEvent("document_executed", case_id, document.id, document.version, ()))
