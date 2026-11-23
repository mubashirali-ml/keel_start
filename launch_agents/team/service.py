"""Members and co-founder invites (ADR-0026). Owned by T-027."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..config import Settings
from ..domain.accounts import CaseAccess, Invite, Membership, User
from ..domain.helpers import utcnow
from ..domain.views import InvitePreview, MemberView
from ..persistence.accounts import AccountsRepository
from ..persistence.repository import Repository
from ..persistence.team import TeamRepository
from ..ports.email import Mailer

__all__ = ["TeamService"]


class TeamService:
    def __init__(
        self,
        team: TeamRepository,
        accounts: AccountsRepository,
        repo: Repository,
        mailer: Mailer,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.team = team
        self.accounts = accounts
        self.repo = repo
        self.mailer = mailer
        self.settings = settings
        self.clock = clock

    def add_owner(self, case_id: str, user: User, *, founder_id: str | None = None) -> Membership:
        raise NotImplementedError("TeamService.add_owner is implemented in T-027")

    def members(self, access: CaseAccess) -> list[MemberView]:
        raise NotImplementedError("TeamService.members is implemented in T-027")

    def invite(self, access: CaseAccess, *, email: str, founder_id: str | None) -> Invite:
        """Needs ``MANAGE_TEAM``; emails a link with a random token (stored hashed, 7 days)."""
        raise NotImplementedError("TeamService.invite is implemented in T-027")

    def list_invites(self, access: CaseAccess) -> list[Invite]:
        raise NotImplementedError("TeamService.list_invites is implemented in T-027")

    def revoke_invite(self, access: CaseAccess, invite_id: str) -> None:
        raise NotImplementedError("TeamService.revoke_invite is implemented in T-027")

    def preview_invite(self, raw_token: str) -> InvitePreview:
        """Public; ``TokenInvalidError`` for an unknown token."""
        raise NotImplementedError("TeamService.preview_invite is implemented in T-027")

    def accept_invite(self, raw_token: str, user: User) -> Membership:
        """The logged-in user's email must match the invite."""
        raise NotImplementedError("TeamService.accept_invite is implemented in T-027")

    def link_founder(self, access: CaseAccess, user_id: str, founder_id: str) -> Membership:
        """Needs ``MANAGE_TEAM``; a founder links to at most one user per company."""
        raise NotImplementedError("TeamService.link_founder is implemented in T-027")

    def remove_member(self, access: CaseAccess, user_id: str) -> None:
        """An owner removes a member, or a member leaves; the last owner cannot leave."""
        raise NotImplementedError("TeamService.remove_member is implemented in T-027")
