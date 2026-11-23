"""Fixed-window rate-limit counters, llm_usage rows, monthly counts per user and pruning (ADR-0033). Owned by T-032.

T-001 provides the class and its constructor; T-032 defines the methods (the ADRs name this
repository by responsibility only).
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["LimitsRepository"]


class LimitsRepository:
    """Fixed-window rate-limit counters, llm_usage rows, monthly counts per user and pruning (ADR-0033)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
