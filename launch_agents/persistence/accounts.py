"""Users, sessions and one-time auth tokens (ADR-0026, ADR-0027). Owned by T-026."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.engine import Engine

from ..domain.accounts import User

__all__ = ["AccountsRepository", "SessionRecord"]


class SessionRecord(BaseModel):
    token_hash: str
    user_id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    ip: str | None = None
    user_agent: str | None = None


class AccountsRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create_user(self, *, email: str, full_name: str, password_hash: str) -> User:
        """``ConflictError`` on a duplicate email."""
        raise NotImplementedError("AccountsRepository.create_user is implemented in T-026")

    def get_user(self, user_id: str) -> User:
        raise NotImplementedError("AccountsRepository.get_user is implemented in T-026")

    def find_user_by_email(self, email: str) -> User | None:
        raise NotImplementedError("AccountsRepository.find_user_by_email is implemented in T-026")

    def get_password_hash(self, user_id: str) -> str:
        raise NotImplementedError("AccountsRepository.get_password_hash is implemented in T-026")

    def set_password_hash(self, user_id: str, h: str) -> None:
        raise NotImplementedError("AccountsRepository.set_password_hash is implemented in T-026")

    def update_user(self, user_id: str, **fields: Any) -> User:
        raise NotImplementedError("AccountsRepository.update_user is implemented in T-026")

    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError("AccountsRepository.delete_user is implemented in T-026")

    def create_session(
        self, *, token_hash: str, user_id: str, expires_at: datetime, ip: str | None, user_agent: str | None
    ) -> None:
        raise NotImplementedError("AccountsRepository.create_session is implemented in T-026")

    def get_session(self, token_hash: str) -> SessionRecord | None:
        raise NotImplementedError("AccountsRepository.get_session is implemented in T-026")

    def touch_session(self, token_hash: str, *, now: datetime, expires_at: datetime) -> None:
        raise NotImplementedError("AccountsRepository.touch_session is implemented in T-026")

    def revoke_session(self, token_hash: str) -> None:
        raise NotImplementedError("AccountsRepository.revoke_session is implemented in T-026")

    def revoke_user_sessions(self, user_id: str, *, except_hash: str | None = None) -> int:
        raise NotImplementedError("AccountsRepository.revoke_user_sessions is implemented in T-026")

    def create_token(self, *, token_hash: str, user_id: str, purpose: str, expires_at: datetime) -> None:
        raise NotImplementedError("AccountsRepository.create_token is implemented in T-026")

    def use_token(self, token_hash: str, purpose: str, *, now: datetime) -> str:
        """Returns the user id; ``TokenInvalidError`` when unknown, expired or already used."""
        raise NotImplementedError("AccountsRepository.use_token is implemented in T-026")

    def list_users(self, *, query: str | None, offset: int, limit: int) -> list[User]:
        """Admin list (ADR-0034)."""
        raise NotImplementedError("AccountsRepository.list_users is implemented in T-026")
