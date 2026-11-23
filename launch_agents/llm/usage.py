"""LLM usage reporting (ADR-0022).

Providers call ``report_usage`` once per attempt and never know which customer they serve;
the metering wrapper (ADR-0033) opens a ``usage_sink`` around each call. Sinks are scoped
with a ``ContextVar`` and nest: a usage reported inside nested sinks reaches every one of them.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator

from pydantic import BaseModel

__all__ = ["LLMUsage", "report_usage", "usage_sink"]


class LLMUsage(BaseModel):
    provider: str
    model: str | None
    task: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int
    ok: bool


_SINKS: ContextVar[tuple[Callable[[LLMUsage], None], ...]] = ContextVar("llm_usage_sinks", default=())


def report_usage(usage: LLMUsage) -> None:
    """Deliver ``usage`` to every active sink (innermost first); a no-op outside any sink."""
    for callback in reversed(_SINKS.get()):
        callback(usage)


@contextmanager
def usage_sink(callback: Callable[[LLMUsage], None]) -> Iterator[None]:
    """Collect every ``LLMUsage`` reported inside the block (also from nested blocks)."""
    token = _SINKS.set(_SINKS.get() + (callback,))
    try:
        yield
    finally:
        _SINKS.reset(token)
