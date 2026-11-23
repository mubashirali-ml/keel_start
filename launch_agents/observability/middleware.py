"""Request id + one log line per request (ADR-0034). Owned by T-033."""

from __future__ import annotations

from typing import Any

__all__ = ["REQUEST_ID_HEADER", "RequestContextMiddleware"]

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """ASGI: accepts an incoming ``X-Request-ID`` matching ``[A-Za-z0-9-]{8,64}`` (else makes
    one), returns it, binds request_id/user_id/case_id to a ContextVar and logs method, route,
    status and duration_ms (T-033)."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        raise NotImplementedError("RequestContextMiddleware is implemented in T-033")
