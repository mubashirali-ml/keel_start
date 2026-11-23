"""Observability: structured logs, request ids, redaction, error reporting (ADR-0034). Owned by T-033."""

from .errors import ErrorReporter, load_error_reporter, report_error
from .logs import RedactingFilter, configure_logging, current_request_id, log_context
from .middleware import REQUEST_ID_HEADER, RequestContextMiddleware

__all__ = [
    "REQUEST_ID_HEADER",
    "ErrorReporter",
    "RedactingFilter",
    "RequestContextMiddleware",
    "configure_logging",
    "current_request_id",
    "load_error_reporter",
    "log_context",
    "report_error",
]
