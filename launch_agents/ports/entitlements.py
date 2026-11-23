"""Entitlements and usage ports (ADR-0030, ADR-0038). ``DbEntitlements`` is in ``billing/`` (T-029)."""

from __future__ import annotations

from typing import Mapping, Protocol, runtime_checkable

from ..domain.billing import PLANS, Entitlements, Plan, PlanId

__all__ = ["EntitlementsProvider", "StaticEntitlements", "UsageCounter"]


@runtime_checkable
class EntitlementsProvider(Protocol):
    def for_user(self, user_id: str | None) -> Entitlements:
        """What the user's plan includes; ``None`` (no billing user) -> Free."""
        ...


class StaticEntitlements:
    """Fake: ``StaticEntitlements(PlanId.LAUNCH)`` returns that plan for everyone (also for ``None``,
    so tests of system work see the configured plan)."""

    def __init__(self, plan: PlanId = PlanId.LAUNCH, plans: Mapping[PlanId, Plan] = PLANS) -> None:
        self.plan = plan
        self.plans = plans

    def for_user(self, user_id: str | None) -> Entitlements:
        return Entitlements.for_plan(self.plan, self.plans)


@runtime_checkable
class UsageCounter(Protocol):
    """Counts the allowance usage shown on the billing page (wired by T-016)."""

    def ai_messages_this_month(self, user_id: str) -> int: ...

    def companies_created(self, user_id: str) -> int: ...
