"""Stripe payment gateway (ADR-0030, ADR-0038). Owned by T-029.

The ``stripe`` package is imported lazily inside the implementation, so this module imports
cleanly without it.
"""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..domain.billing import BillingInterval, CheckoutSession, PaymentEvent

__all__ = ["StripePaymentGateway"]


class StripePaymentGateway:
    """``PaymentGateway`` over the Stripe SDK: Checkout, customer portal, signed webhooks,
    price changes with proration and price lookups. ``live`` is True only with ``sk_live_`` keys."""

    name = "stripe"

    def __init__(self, settings: Settings, *, client: Any = None) -> None:
        self.settings = settings
        self.client = client
        self.live = bool(settings.stripe_secret_key and settings.stripe_secret_key.startswith("sk_live_"))

    def create_customer(self, *, email: str, user_id: str) -> str:
        raise NotImplementedError("StripePaymentGateway.create_customer is implemented in T-029")

    def create_checkout_session(
        self, *, customer_id: str, price_id: str, user_id: str, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        raise NotImplementedError("StripePaymentGateway.create_checkout_session is implemented in T-029")

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        raise NotImplementedError("StripePaymentGateway.create_portal_session is implemented in T-029")

    def parse_webhook(self, payload: bytes, signature_header: str | None) -> PaymentEvent:
        raise NotImplementedError("StripePaymentGateway.parse_webhook is implemented in T-029")

    def change_subscription_price(self, *, subscription_id: str, price_id: str) -> PaymentEvent:
        raise NotImplementedError("StripePaymentGateway.change_subscription_price is implemented in T-029")

    def price_amount(self, price_id: str) -> tuple[int, BillingInterval] | None:
        raise NotImplementedError("StripePaymentGateway.price_amount is implemented in T-029")
