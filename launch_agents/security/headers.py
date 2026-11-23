"""Security headers on every response (ADR-0033). Owned by T-032."""

from __future__ import annotations

from typing import Any

from ..config import Settings

__all__ = ["SecurityHeadersMiddleware", "security_headers"]


def security_headers(path: str, settings: Settings) -> dict[str, str]:
    """The ADR-0033 headers for a response to ``path`` (HSTS in production only; the website
    preview gets the sandbox CSP and ``frame-ancestors 'self'``) (T-032)."""
    raise NotImplementedError("security_headers is implemented in T-032")


class SecurityHeadersMiddleware:
    """ASGI middleware adding ``security_headers(path, settings)`` to every response (T-032)."""

    def __init__(self, app: Any, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        raise NotImplementedError("SecurityHeadersMiddleware is implemented in T-032")
