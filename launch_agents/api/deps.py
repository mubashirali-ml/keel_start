"""FastAPI dependencies (ADR-0026, ADR-0032, ADR-0033). ``get_services`` is T-001's; the rest
are T-016's (exact names and roles fixed here so the route tickets can import them)."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Request, Response

from ..composition import Services
from ..config import Settings
from ..domain.accounts import CaseAccess, Permission, RequestContext, User
from ..domain.errors import RetryableError

__all__ = [
    "clear_session_cookie",
    "get_ctx",
    "get_services",
    "rate_limit",
    "require_admin",
    "require_case",
    "require_user",
    "set_session_cookie",
]


def get_services(request: Request) -> Services:
    """The only dependency routes use to reach the services (``app.state.services``)."""
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RetryableError("The service is still starting up. Please try again in a moment.")
    return services


def get_ctx(request: Request) -> RequestContext:
    """``RequestContext`` from the ``la_session`` cookie, client IP (``TRUSTED_PROXY_COUNT``),
    user agent and, in demo mode only, ``X-Act-As-Founder`` (T-016)."""
    raise NotImplementedError("get_ctx is implemented in T-016")


def require_user(request: Request) -> User:
    """The logged-in user; ``AuthRequiredError`` otherwise (T-016)."""
    raise NotImplementedError("require_user is implemented in T-016")


def require_admin(request: Request) -> User:
    """A logged-in platform admin; ``ForbiddenError`` otherwise (T-016)."""
    raise NotImplementedError("require_admin is implemented in T-016")


def require_case(permission: Permission) -> Callable[..., CaseAccess]:
    """Dependency factory: ``authorize_case`` for the path's company id and ``permission`` (T-016)."""
    raise NotImplementedError("require_case is implemented in T-016")


def rate_limit(cls: str) -> Callable[..., Any]:
    """Dependency factory applying the ADR-0033 rate-limit class ``cls`` (T-016)."""
    raise NotImplementedError("rate_limit is implemented in T-016")


def set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """``la_session``: HttpOnly, SameSite=Lax, Path=/, Secure in production (ADR-0033, T-016)."""
    raise NotImplementedError("set_session_cookie is implemented in T-016")


def clear_session_cookie(response: Response, settings: Settings) -> None:
    raise NotImplementedError("clear_session_cookie is implemented in T-016")
