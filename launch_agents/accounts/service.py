"""Sign-up, login, sessions, email verification and password reset (ADR-0026). Owned by T-026."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from pydantic import BaseModel

from ..config import Settings
from ..domain.accounts import RequestContext, User
from ..domain.helpers import utcnow
from ..persistence.accounts import AccountsRepository
from ..ports.email import Mailer

__all__ = ["AuthService", "SessionToken"]


class SessionToken(BaseModel):
    raw: str  # goes into the la_session cookie; only its SHA-256 hash is stored
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        accounts: AccountsRepository,
        mailer: Mailer,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.accounts = accounts
        self.mailer = mailer
        self.settings = settings
        self.clock = clock

    def signup(self, email: str, password: str, full_name: str, *, ctx: RequestContext) -> tuple[User, SessionToken]:
        raise NotImplementedError("AuthService.signup is implemented in T-026")

    def login(self, email: str, password: str, *, ctx: RequestContext) -> tuple[User, SessionToken]:
        """``InvalidCredentialsError`` without revealing whether the email exists."""
        raise NotImplementedError("AuthService.login is implemented in T-026")

    def logout(self, raw_token: str) -> None:
        raise NotImplementedError("AuthService.logout is implemented in T-026")

    def resolve_session(self, raw_token: str, *, touch: bool = True) -> User | None:
        """The session's user; None if missing, expired or revoked."""
        raise NotImplementedError("AuthService.resolve_session is implemented in T-026")

    def request_email_verification(self, user: User) -> None:
        raise NotImplementedError("AuthService.request_email_verification is implemented in T-026")

    def verify_email(self, raw_token: str) -> User:
        """``TokenInvalidError`` for an unknown, expired or used token."""
        raise NotImplementedError("AuthService.verify_email is implemented in T-026")

    def request_password_reset(self, email: str, *, ctx: RequestContext) -> None:
        """Silent for unknown emails."""
        raise NotImplementedError("AuthService.request_password_reset is implemented in T-026")

    def reset_password(self, raw_token: str, new_password: str) -> None:
        """Revokes every session of the user."""
        raise NotImplementedError("AuthService.reset_password is implemented in T-026")

    def change_password(self, user: User, current: str, new: str, *, keep_session: str) -> None:
        raise NotImplementedError("AuthService.change_password is implemented in T-026")

    def update_profile(self, user: User, *, full_name: str) -> User:
        raise NotImplementedError("AuthService.update_profile is implemented in T-026")
