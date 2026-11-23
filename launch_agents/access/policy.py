"""Who may do what in a company (ADR-0026). ``ROLE_PERMISSIONS`` is fixed by T-001;
``authorize_case`` is implemented by T-027."""

from __future__ import annotations

from typing import Mapping

from ..domain.accounts import ALL_PERMISSIONS, CaseAccess, MemberRole, Permission, RequestContext
from ..persistence.repository import Repository
from ..persistence.team import TeamRepository
from ..ports.entitlements import EntitlementsProvider

__all__ = ["ROLE_PERMISSIONS", "authorize_case"]

ROLE_PERMISSIONS: Mapping[MemberRole, frozenset[Permission]] = {
    MemberRole.OWNER: ALL_PERMISSIONS,
    MemberRole.MEMBER: ALL_PERMISSIONS - {Permission.MANAGE_TEAM, Permission.DELETE_COMPANY},
}


def authorize_case(
    ctx: RequestContext,
    case_id: str,
    permission: Permission,
    *,
    team: TeamRepository,
    repo: Repository,
    entitlements: EntitlementsProvider,
) -> CaseAccess:
    """No user -> ``AuthRequiredError``; unknown company or not a member -> ``NotFoundError``;
    missing permission -> ``ForbiddenError``; ``SIGN`` / ``EDIT_DOCUMENTS`` need a linked
    founder; demo-mode act-as per ADR-0026 (T-027)."""
    raise NotImplementedError("authorize_case is implemented in T-027")
