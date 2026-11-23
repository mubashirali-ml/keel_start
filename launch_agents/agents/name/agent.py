"""The Name Agent: name ideas with live domain checks (ADR-0009, ADR-0011). Owned by T-007."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from ...domain.messages import AgentId
from ...domain.state import NameCandidate
from ...domain.types import CaseFacts
from ...llm.provider import LLMProvider
from ...ports.domain_check import DomainChecker
from ..base import AgentContext, AgentReply

__all__ = ["NameAgent", "NameIntent", "NameSuggestion", "NameSuggestions", "check_candidate", "suggest_names"]


class NameSuggestion(BaseModel):
    name: str
    rationale: str


class NameSuggestions(BaseModel):
    """Output of the ``name.suggest`` task (ADR-0010)."""

    names: list[NameSuggestion]


class NameIntent(BaseModel):
    """Output of the ``name.intent`` task (ADR-0010)."""

    intent: Literal["suggest", "choose", "check", "question"]
    name: str | None
    index: int | None


class NameAgent:
    """Specialist (``AgentId.NAME``): suggests names, checks .com/.co/.io, returns ``ChooseName``."""

    agent_id = AgentId.NAME

    def handle(self, ctx: AgentContext) -> AgentReply:
        raise NotImplementedError("NameAgent.handle is implemented in T-007")


def suggest_names(facts: CaseFacts, llm: LLMProvider, count: int = 5) -> list[NameSuggestion]:
    """``count`` name ideas from the business description (task ``name.suggest``, T-007)."""
    raise NotImplementedError("suggest_names is implemented in T-007")


def check_candidate(
    suggestion: NameSuggestion, checker: DomainChecker, state_code: str | None, now: datetime
) -> NameCandidate:
    """Domain checks in ``DOMAIN_TLDS`` order plus the state name-search and USPTO links (T-007)."""
    raise NotImplementedError("check_candidate is implemented in T-007")
