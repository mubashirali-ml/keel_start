"""Per-account AI usage limits (ADR-0033, ADR-0038). Owned by T-032."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..domain.helpers import utcnow
from ..llm.provider import LLMProvider, LLMRequest, T
from ..persistence.limits import LimitsRepository

__all__ = ["MeteredLLM"]


class MeteredLLM:
    """``LLMProvider`` wrapper: ``UsageLimitError`` before the call once this month's allowance
    is used; one ``llm_usage`` row per call via ``usage_sink`` (T-032)."""

    def __init__(
        self,
        inner: LLMProvider,
        limits: LimitsRepository,
        *,
        user_id: str | None,
        case_id: str | None,
        monthly_limit: int,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.inner = inner
        self.limits = limits
        self.user_id = user_id
        self.case_id = case_id
        self.monthly_limit = monthly_limit
        self.clock = clock
        self.name = inner.name

    def complete(self, request: LLMRequest) -> str:
        raise NotImplementedError("MeteredLLM.complete is implemented in T-032")

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T:
        raise NotImplementedError("MeteredLLM.complete_json is implemented in T-032")
