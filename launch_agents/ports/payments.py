"""Payment gateway port and the fake gateway (ADR-0030, ADR-0038).

The Stripe adapter is ``adapters/stripe_payments.py`` (T-029). The fake stands in for Stripe in
development, tests and the demo: its checkout URL opens the in-app test-checkout page, and
``complete_checkout`` / ``cancel`` / ``change_subscription_price`` produce the events Stripe
would send, signed so that its own ``parse_webhook`` accepts them (and rejects tampering).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any, Callable, Protocol, runtime_checkable
from urllib.parse import quote

from ..config import Settings, load_settings
from ..domain.billing import (
    BillingInterval,
    CheckoutSession,
    PaymentEvent,
    PlanId,
    SubscriptionStatus,
)
from ..domain.errors import InvalidStateError, WebhookSignatureError
from ..domain.helpers import utcnow

__all__ = ["FAKE_WEBHOOK_SECRET", "FakePaymentGateway", "PaymentGateway", "fake_price_id"]

FAKE_WEBHOOK_SECRET = "whsec_fake_gateway_secret"


@runtime_checkable
class PaymentGateway(Protocol):
    name: str
    live: bool  # True only with sk_live_ keys

    def create_customer(self, *, email: str, user_id: str) -> str: ...

    def create_checkout_session(
        self, *, customer_id: str, price_id: str, user_id: str, success_url: str, cancel_url: str
    ) -> CheckoutSession: ...

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str: ...

    def parse_webhook(self, payload: bytes, signature_header: str | None) -> PaymentEvent:
        """Verify and parse a webhook; ``WebhookSignatureError`` when the signature is wrong."""
        ...

    def change_subscription_price(self, *, subscription_id: str, price_id: str) -> PaymentEvent:
        """Switch the subscription to another price with proration (ADR-0038)."""
        ...

    def price_amount(self, price_id: str) -> tuple[int, BillingInterval] | None:
        """The provider's amount (cents) and interval for a price id; None if unknown."""
        ...


def fake_price_id(plan: PlanId, interval: BillingInterval) -> str:
    """The fake gateway's own price id for a plan and interval, e.g. ``price_fake_launch_monthly``."""
    return f"price_fake_{plan.value}_{'monthly' if interval == BillingInterval.MONTH else 'yearly'}"


class FakePaymentGateway:
    """In-memory ``PaymentGateway``: name ``fake``, never live.

    ``delivered`` holds ``(payload, signature_header)`` for every event produced, in order, as
    the webhook endpoint would receive them; ``sign_event`` signs any event the same way.
    """

    name = "fake"
    live = False

    def __init__(self, settings: Settings | None = None, *, clock: Callable[[], datetime] = utcnow) -> None:
        self.settings = settings if settings is not None else load_settings({"APP_ENV": "test"})
        self.base_url = self.settings.app_base_url.rstrip("/")
        self.webhook_secret = self.settings.stripe_webhook_secret or FAKE_WEBHOOK_SECRET
        self.clock = clock
        self.customers: dict[str, dict[str, str]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.delivered: list[tuple[bytes, str]] = []
        self._counter = 0

    # -- helpers ---------------------------------------------------------------------
    def _next(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_fake_{self._counter:06d}"

    def _prices(self) -> dict[str, tuple[int, BillingInterval]]:
        s = self.settings
        configured = {
            (PlanId.LAUNCH, BillingInterval.MONTH): s.stripe_price_launch_monthly,
            (PlanId.LAUNCH, BillingInterval.YEAR): s.stripe_price_launch_yearly,
            (PlanId.TEAM, BillingInterval.MONTH): s.stripe_price_team_monthly,
            (PlanId.TEAM, BillingInterval.YEAR): s.stripe_price_team_yearly,
        }
        plans = s.plans()
        prices: dict[str, tuple[int, BillingInterval]] = {}
        for (plan_id, interval), configured_id in configured.items():
            plan = plans[plan_id]
            cents = plan.price_month_cents if interval == BillingInterval.MONTH else plan.price_year_cents
            prices[fake_price_id(plan_id, interval)] = (cents, interval)
            if configured_id:
                prices[configured_id] = (cents, interval)
        return prices

    def _period_end(self, price_id: str) -> datetime:
        interval = self._prices().get(price_id, (0, BillingInterval.MONTH))[1]
        return self.clock() + (timedelta(days=365) if interval == BillingInterval.YEAR else timedelta(days=30))

    def _subscription_for_customer(self, customer_id: str) -> tuple[str, dict[str, Any]]:
        for sub_id, sub in reversed(list(self.subscriptions.items())):
            if sub["customer_id"] == customer_id and sub["status"] != SubscriptionStatus.CANCELED:
                return sub_id, sub
        raise InvalidStateError("There is no active subscription to cancel.")

    def _event(self, type_: str, sub_id: str, sub: dict[str, Any], *, client_reference_id: str | None = None) -> PaymentEvent:
        event = PaymentEvent(
            id=self._next("evt"),
            type=type_,
            customer_id=sub["customer_id"],
            subscription_id=sub_id,
            client_reference_id=client_reference_id or sub.get("user_id"),
            price_id=sub["price_id"],
            status=sub["status"],
            current_period_end=sub["current_period_end"],
            cancel_at_period_end=sub["cancel_at_period_end"],
        )
        self.delivered.append(self.sign_event(event))
        return event

    # -- PaymentGateway --------------------------------------------------------------
    def create_customer(self, *, email: str, user_id: str) -> str:
        customer_id = self._next("cus")
        self.customers[customer_id] = {"email": email, "user_id": user_id}
        return customer_id

    def create_checkout_session(
        self, *, customer_id: str, price_id: str, user_id: str, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        session_id = self._next("cs")
        self.sessions[session_id] = {
            "customer_id": customer_id,
            "price_id": price_id,
            "user_id": user_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "completed": False,
        }
        return CheckoutSession(id=session_id, url=f"{self.base_url}/app/billing/test-checkout?session={quote(session_id)}")

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        separator = "&" if "?" in return_url else "?"
        return f"{return_url}{separator}portal=fake&customer={quote(customer_id)}"

    def change_subscription_price(self, *, subscription_id: str, price_id: str) -> PaymentEvent:
        sub = self.subscriptions.get(subscription_id)
        if sub is None or sub["status"] == SubscriptionStatus.CANCELED:
            raise InvalidStateError("There is no active subscription to change.")
        sub.update(price_id=price_id, current_period_end=self._period_end(price_id))
        return self._event("customer.subscription.updated", subscription_id, sub)

    def price_amount(self, price_id: str) -> tuple[int, BillingInterval] | None:
        return self._prices().get(price_id)

    # -- fake-only controls ----------------------------------------------------------
    def complete_checkout(self, session_id: str) -> PaymentEvent:
        """Pay a test checkout session: creates the subscription, returns ``checkout.session.completed``."""
        session = self.sessions.get(session_id)
        if session is None:
            raise InvalidStateError("This test checkout session doesn't exist.")
        if session["completed"]:
            raise InvalidStateError("This test checkout session is already paid.")
        session["completed"] = True
        sub_id = self._next("sub")
        self.subscriptions[sub_id] = {
            "customer_id": session["customer_id"],
            "user_id": session["user_id"],
            "price_id": session["price_id"],
            "status": SubscriptionStatus.ACTIVE,
            "current_period_end": self._period_end(session["price_id"]),
            "cancel_at_period_end": False,
        }
        session["subscription_id"] = sub_id
        return self._event("checkout.session.completed", sub_id, self.subscriptions[sub_id], client_reference_id=session["user_id"])

    def cancel(self, customer_id: str, *, at_period_end: bool = False) -> PaymentEvent:
        """Cancel the customer's subscription: immediately (``customer.subscription.deleted``) or at
        the period end (``customer.subscription.updated`` with ``cancel_at_period_end``)."""
        sub_id, sub = self._subscription_for_customer(customer_id)
        if at_period_end:
            sub["cancel_at_period_end"] = True
            return self._event("customer.subscription.updated", sub_id, sub)
        sub["status"] = SubscriptionStatus.CANCELED
        return self._event("customer.subscription.deleted", sub_id, sub)

    # -- webhooks --------------------------------------------------------------------
    def _signature(self, timestamp: str, payload: bytes) -> str:
        return hmac.new(self.webhook_secret.encode("utf-8"), timestamp.encode("ascii") + b"." + payload, hashlib.sha256).hexdigest()

    def sign_event(self, event: PaymentEvent) -> tuple[bytes, str]:
        """``(payload, signature_header)`` exactly as the webhook endpoint receives them."""
        body = {
            "id": event.id,
            "object": "event",
            "type": event.type,
            "data": {"object": event.model_dump(mode="json", exclude={"id", "type"})},
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        timestamp = str(int(self.clock().timestamp()))
        return payload, f"t={timestamp},v1={self._signature(timestamp, payload)}"

    def parse_webhook(self, payload: bytes, signature_header: str | None) -> PaymentEvent:
        invalid = WebhookSignatureError("This payment notification could not be verified.")
        if not signature_header:
            raise invalid
        parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
        timestamp, given = parts.get("t"), parts.get("v1")
        if not timestamp or not given or not (timestamp.isascii() and given.isascii()):
            raise invalid
        if not hmac.compare_digest(self._signature(timestamp, payload), given):
            raise invalid
        try:
            body = json.loads(payload)
            return PaymentEvent(id=body["id"], type=body["type"], **body["data"]["object"])
        except (ValueError, KeyError, TypeError) as exc:
            raise WebhookSignatureError("This payment notification could not be read.") from exc
