"""Billing: plans, checkout, plan switch, portal, webhooks, entitlements (ADR-0030, ADR-0038). Owned by T-029."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping

from ..config import Settings
from ..domain.accounts import User
from ..domain.billing import (
    BillingInterval,
    CheckoutSession,
    Entitlements,
    Plan,
    PlanId,
    PriceCheck,
    Subscription,
)
from ..domain.helpers import utcnow
from ..domain.views import BillingOverview
from ..persistence.accounts import AccountsRepository
from ..persistence.billing import BillingRepository
from ..ports.entitlements import UsageCounter
from ..ports.payments import PaymentGateway

__all__ = ["BillingService", "DbEntitlements", "plan_for_price", "price_id_for"]


class BillingService:
    def __init__(
        self,
        billing: BillingRepository,
        accounts: AccountsRepository,
        gateway: PaymentGateway,
        settings: Settings,
        *,
        usage: UsageCounter | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.billing = billing
        self.accounts = accounts
        self.gateway = gateway
        self.settings = settings
        self.usage = usage
        self.clock = clock

    def plans(self) -> list[Plan]:
        """``settings.plans()`` by rank."""
        raise NotImplementedError("BillingService.plans is implemented in T-029")

    def subscription(self, user: User) -> Subscription:
        raise NotImplementedError("BillingService.subscription is implemented in T-029")

    def overview(self, user: User) -> BillingOverview:
        """Usage zeros when no ``UsageCounter`` was given."""
        raise NotImplementedError("BillingService.overview is implemented in T-029")

    def start_checkout(self, user: User, plan: PlanId, interval: BillingInterval) -> CheckoutSession:
        """FREE, unknown plan or yearly while disabled -> ``InvalidStateError``; an active paid
        subscription -> ``ConflictError``."""
        raise NotImplementedError("BillingService.start_checkout is implemented in T-029")

    def change_plan(self, user: User, plan: PlanId, interval: BillingInterval) -> Subscription:
        """Switch the existing subscription with proration (ADR-0038)."""
        raise NotImplementedError("BillingService.change_plan is implemented in T-029")

    def portal_url(self, user: User) -> str:
        """``ConflictError`` if the user never subscribed."""
        raise NotImplementedError("BillingService.portal_url is implemented in T-029")

    def handle_webhook(self, payload: bytes, signature_header: str | None) -> None:
        """Idempotent: each event id is recorded first and processed once."""
        raise NotImplementedError("BillingService.handle_webhook is implemented in T-029")

    def complete_test_checkout(self, session_id: str) -> None:
        """Fake gateway only, else ``ForbiddenError``."""
        raise NotImplementedError("BillingService.complete_test_checkout is implemented in T-029")

    def check_prices(self) -> list[PriceCheck]:
        """Each paid plan x interval: configured amount vs. the gateway's (ADR-0038)."""
        raise NotImplementedError("BillingService.check_prices is implemented in T-029")


class DbEntitlements:
    """``EntitlementsProvider`` over the subscriptions table: ACTIVE / TRIALING / PAST_DUE ->
    the subscribed plan, anything else -> Free."""

    def __init__(self, billing: BillingRepository, plans: Mapping[PlanId, Plan]) -> None:
        self.billing = billing
        self.plans = plans

    def for_user(self, user_id: str | None) -> Entitlements:
        raise NotImplementedError("DbEntitlements.for_user is implemented in T-029")


def price_id_for(settings: Settings, plan: PlanId, interval: BillingInterval) -> str:
    """The configured Stripe price id for a paid plan and interval (T-029)."""
    raise NotImplementedError("price_id_for is implemented in T-029")


def plan_for_price(settings: Settings, price_id: str) -> tuple[PlanId, BillingInterval] | None:
    """Reverse lookup for webhooks; None for an unknown price id (T-029)."""
    raise NotImplementedError("plan_for_price is implemented in T-029")
