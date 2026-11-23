"""Pluggable error reporting (ADR-0034). Owned by T-033."""

from __future__ import annotations

from typing import Any, Callable, Mapping

__all__ = ["ErrorReporter", "load_error_reporter", "report_error"]

ErrorReporter = Callable[[BaseException, Mapping[str, Any]], None]


def load_error_reporter(dotted: str | None) -> ErrorReporter:
    """``"pkg.module:function"``; None -> the default reporter, which logs at ERROR (T-033)."""
    raise NotImplementedError("load_error_reporter is implemented in T-033")


def report_error(exc: BaseException, **context: Any) -> None:
    """Report an unhandled error with request id, route, user id, job id; never raises (T-033)."""
    raise NotImplementedError("report_error is implemented in T-033")
