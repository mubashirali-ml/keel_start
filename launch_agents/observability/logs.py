"""Structured logs with request ids and redaction (ADR-0033, ADR-0034). Owned by T-033."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from ..config import Settings

__all__ = ["RedactingFilter", "configure_logging", "current_request_id", "log_context"]


def configure_logging(settings: Settings) -> None:
    """JSON (production) or text logs at ``settings.log_level`` with the redaction filter (T-033)."""
    raise NotImplementedError("configure_logging is implemented in T-033")


class RedactingFilter(logging.Filter):
    """Masks secrets, tokens, cookies and emails (``a***@example.com``) in log records (T-033)."""

    def filter(self, record: logging.LogRecord) -> bool:
        raise NotImplementedError("RedactingFilter is implemented in T-033")


@contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Bind fields (request_id, user_id, case_id, job_id, ...) to every log line inside the block (T-033)."""
    raise NotImplementedError("log_context is implemented in T-033")
    yield  # pragma: no cover


def current_request_id() -> str | None:
    """The request id bound to the current context, if any (T-033)."""
    raise NotImplementedError("current_request_id is implemented in T-033")
