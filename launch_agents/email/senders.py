"""Development and test-run email transports (ADR-0029). Owned by T-028.

``ConsoleEmailSender`` logs recipient, subject and link (development); ``FileDropEmailSender``
appends each message as one JSON line to ``EMAIL_DROP_FILE`` (browser runs and the demo
read emails from another process; refused in production).
"""

from __future__ import annotations

from pathlib import Path

from ..domain.email import EmailMessage, SendResult

__all__ = ["ConsoleEmailSender", "FileDropEmailSender"]


class ConsoleEmailSender:
    name = "console"

    def send(self, message: EmailMessage) -> SendResult:
        raise NotImplementedError("ConsoleEmailSender.send is implemented in T-028")


class FileDropEmailSender:
    name = "file_drop"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def send(self, message: EmailMessage) -> SendResult:
        raise NotImplementedError("FileDropEmailSender.send is implemented in T-028")
