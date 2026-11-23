"""Fixed-window rate limits stored in ``rate_limits`` (ADR-0033). Owned by T-032.

``RATE_LIMITS`` is the ADR-0033 table: each rule's ``name`` is the key it counts by
(``ip``, ``email`` or ``user``), so ``hit(cls, keys={"ip": ..., "email": ...})``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping

from pydantic import BaseModel

from ..domain.helpers import utcnow
from ..persistence.limits import LimitsRepository

__all__ = ["RATE_LIMITS", "RateLimitRule", "RateLimiter"]


class RateLimitRule(BaseModel):
    name: str
    limit: int
    window_s: int


RATE_LIMITS: Mapping[str, list[RateLimitRule]] = {
    # login, signup, reset, password change
    "auth": [RateLimitRule(name="ip", limit=10, window_s=15 * 60), RateLimitRule(name="email", limit=5, window_s=15 * 60)],
    # forgot password, resend verification
    "email": [RateLimitRule(name="email", limit=3, window_s=3600), RateLimitRule(name="ip", limit=10, window_s=3600)],
    # chat message, name recheck, website build
    "llm": [RateLimitRule(name="user", limit=20, window_s=60), RateLimitRule(name="user", limit=300, window_s=86400)],
    "invite": [RateLimitRule(name="user", limit=20, window_s=86400)],
}


class RateLimiter:
    def __init__(self, limits: LimitsRepository, *, enabled: bool, clock: Callable[[], datetime] = utcnow) -> None:
        self.limits = limits
        self.enabled = enabled
        self.clock = clock

    def hit(self, cls: str, *, keys: Mapping[str, str]) -> None:
        """Count one hit per rule of ``cls``; ``RateLimitedError`` (``details.retry_after_s``) over a limit."""
        raise NotImplementedError("RateLimiter.hit is implemented in T-032")
