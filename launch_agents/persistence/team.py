"""Memberships and invites (ADR-0026, ADR-0027). Owned by T-027."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.engine import Engine

from ..domain.accounts import Invite, Membership

__all__ = ["TeamRepository"]


class TeamRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add_member(self, m: Membership) -> Membership:
        raise NotImplementedError("TeamRepository.add_member is implemented in T-027")

    def get_membership(self, case_id: str, user_id: str) -> Membership | None:
        raise NotImplementedError("TeamRepository.get_membership is implemented in T-027")

    def list_members(self, case_id: str) -> list[Membership]:
        raise NotImplementedError("TeamRepository.list_members is implemented in T-027")

    def member_case_ids(self, user_id: str) -> list[str]:
        raise NotImplementedError("TeamRepository.member_case_ids is implemented in T-027")

    def update_member(self, case_id: str, user_id: str, **fields: Any) -> Membership:
        raise NotImplementedError("TeamRepository.update_member is implemented in T-027")

    def remove_member(self, case_id: str, user_id: str) -> None:
        raise NotImplementedError("TeamRepository.remove_member is implemented in T-027")

    def create_invite(self, invite: Invite, *, token_hash: str) -> Invite:
        raise NotImplementedError("TeamRepository.create_invite is implemented in T-027")

    def find_invite_by_token(self, token_hash: str) -> Invite | None:
        raise NotImplementedError("TeamRepository.find_invite_by_token is implemented in T-027")

    def list_invites(self, case_id: str) -> list[Invite]:
        raise NotImplementedError("TeamRepository.list_invites is implemented in T-027")

    def mark_invite(
        self, invite_id: str, *, accepted_at: datetime | None = None, revoked_at: datetime | None = None
    ) -> Invite:
        raise NotImplementedError("TeamRepository.mark_invite is implemented in T-027")
