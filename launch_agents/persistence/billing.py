"""Subscriptions (the only source of a user's plan) and billing events processed once (ADR-0030, ADR-0038). Owned by T-029.

T-001 provides the class and its constructor; T-029 defines the methods (the ADRs name this
repository by responsibility only).
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["BillingRepository"]


class BillingRepository:
    """Subscriptions (the only source of a user's plan) and billing events processed once (ADR-0030, ADR-0038)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
