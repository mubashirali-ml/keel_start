"""Users, memberships, the request context and case access (ADR-0026).

Every service from wave 2 on receives the caller as a ``RequestContext`` (no company yet)
or a ``CaseAccess`` (proof that the caller may touch this company). Only ``api/`` knows
about HTTP requests, cookies and headers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from .billing import Entitlements, Feature, feature_required_message, lowest_plan_with
from .errors import AuthRequiredError, ForbiddenError, PlanRequiredError

__all__ = [
    "ALL_PERMISSIONS",
    "Actor",
    "CaseAccess",
    "Invite",
    "MemberRole",
    "Membership",
    "Permission",
    "RequestContext",
    "User",
]


class User(BaseModel):
    id: str
    email: str
    full_name: str
    email_verified_at: datetime | None = None
    is_admin: bool = False
    created_at: datetime

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class MemberRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"


class Membership(BaseModel):
    case_id: str
    user_id: str
    role: MemberRole
    founder_id: str | None
    joined_at: datetime


class Invite(BaseModel):
    id: str
    case_id: str
    email: str
    founder_id: str | None
    invited_by: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None


class Permission(str, Enum):
    VIEW = "view"
    CHAT = "chat"
    SIGN = "sign"
    EDIT_DOCUMENTS = "edit_documents"
    BUILD_WEBSITE = "build_website"
    DEPLOY = "deploy"
    TICK_GUIDE = "tick_guide"
    MANAGE_TEAM = "manage_team"
    DELETE_COMPANY = "delete_company"


ALL_PERMISSIONS: frozenset[Permission] = frozenset(Permission)


@dataclass(frozen=True)
class RequestContext:
    """Who is calling, built by the API for every request (T-016)."""

    request_id: str
    user: User | None
    ip: str | None = None
    user_agent: str | None = None
    demo_mode: bool = False
    act_as_founder_id: str | None = None  # X-Act-As-Founder header, honoured only in demo mode

    def require_user(self) -> User:
        """The logged-in user; ``AuthRequiredError`` when nobody is logged in."""
        if self.user is None:
            raise AuthRequiredError("Please log in to continue.")
        return self.user

    @classmethod
    def system(cls, request_id: str = "system") -> "RequestContext":
        """A context for work the system does on its own (jobs, sweeps, seeding)."""
        return cls(request_id=request_id, user=None)


@dataclass(frozen=True)
class Actor:
    """Who performs an action, for audit entries and signature evidence."""

    kind: Literal["user", "system"]
    user_id: str | None
    founder_id: str | None
    ip: str | None
    user_agent: str | None
    request_id: str
    acted_by_user_id: str | None = None  # demo act-as: the logged-in user behind the actor

    @property
    def audit_actor(self) -> str:
        """The audit ``actor`` string: founder id, else user id, else ``"system"``."""
        return self.founder_id or self.user_id or "system"


@dataclass(frozen=True)
class CaseAccess:
    """Proof that the caller may touch this company (from ``access.authorize_case``)."""

    case_id: str
    actor: Actor
    membership: Membership | None  # None only for system access
    permissions: frozenset[Permission]
    entitlements: Entitlements  # of the company's billing user (ADR-0030)
    billing_user_id: str | None

    @property
    def founder_id(self) -> str | None:
        return self.actor.founder_id

    def require(self, permission: Permission) -> None:
        """``ForbiddenError`` unless the caller holds ``permission`` in this company."""
        if permission not in self.permissions:
            raise ForbiddenError(
                "You don't have permission to do that in this company.",
                details={"permission": permission.value},
            )

    def require_feature(self, feature: Feature) -> None:
        """``PlanRequiredError`` unless the company's plan includes ``feature`` (ADR-0038).

        The error details carry ``feature`` and ``required_plan`` (the cheapest plan with it).
        """
        if not self.entitlements.has(feature):
            raise PlanRequiredError(
                feature_required_message(feature),
                details={"feature": feature.value, "required_plan": lowest_plan_with(feature).id.value},
            )

    @classmethod
    def system(
        cls,
        case_id: str,
        entitlements: Entitlements,
        *,
        billing_user_id: str | None = None,
        request_id: str = "system",
    ) -> "CaseAccess":
        """Access for the system itself: every permission, actor ``"system"``."""
        actor = Actor(kind="system", user_id=None, founder_id=None, ip=None, user_agent=None, request_id=request_id)
        return cls(
            case_id=case_id,
            actor=actor,
            membership=None,
            permissions=ALL_PERMISSIONS,
            entitlements=entitlements,
            billing_user_id=billing_user_id,
        )
