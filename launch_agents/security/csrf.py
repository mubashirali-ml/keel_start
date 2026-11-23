"""Double-submit CSRF protection for cookie auth (ADR-0033). Owned by T-032."""

from __future__ import annotations

from ..config import Settings

__all__ = ["CSRF_COOKIE", "CSRF_EXEMPT_PATHS", "CSRF_HEADER", "SESSION_COOKIE", "check_csrf", "issue_csrf_token"]

SESSION_COOKIE = "la_session"
CSRF_COOKIE = "la_csrf"
CSRF_HEADER = "X-CSRF-Token"
CSRF_EXEMPT_PATHS = frozenset({"/api/billing/webhook"})  # Stripe signature instead


def issue_csrf_token(secret: str, session_key: str) -> str:
    """``HMAC(SECRET_KEY, session token hash or anonymous nonce)`` (T-032)."""
    raise NotImplementedError("issue_csrf_token is implemented in T-032")


def check_csrf(
    method: str,
    path: str,
    header_token: str | None,
    cookie_token: str | None,
    origin: str | None,
    settings: Settings,
) -> None:
    """Unsafe methods under ``/api`` need header == cookie and an allowed ``Origin``; else
    ``CsrfError`` (T-032)."""
    raise NotImplementedError("check_csrf is implemented in T-032")
