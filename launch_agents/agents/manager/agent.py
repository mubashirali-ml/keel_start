"""The Manager Agent: fact gathering, confirmation and small talk (ADR-0009). Owned by T-012.

T-001 provides the types and exact signatures; T-012 implements the behaviour.
"""

from __future__ import annotations

from pydantic import BaseModel

from ...domain.messages import AgentId, ChatMessage
from ...domain.types import CaseFacts, FactsPatch, ValidationResult
from ..base import AgentContext, AgentReply

__all__ = ["ManagerAgent", "ManagerExtraction", "RouteDecision", "facts_summary", "next_question"]


class ManagerExtraction(BaseModel):
    """Output of the ``manager.extract`` task (ADR-0010)."""

    facts: FactsPatch
    confirms_summary: bool


class RouteDecision(BaseModel):
    """Output of the ``manager.route`` task (ADR-0010)."""

    target: AgentId
    reason: str


class ManagerAgent:
    """Replies when the route target is the Manager: validation issues first, then the next
    missing fact, then a summary to confirm; returns ``LockFacts`` on confirmation (ADR-0009)."""

    agent_id = AgentId.MANAGER

    def handle(self, ctx: AgentContext) -> AgentReply:
        raise NotImplementedError("ManagerAgent.handle is implemented in T-012")


def next_question(result: ValidationResult) -> ChatMessage:
    """The Manager's question for the first issue or missing fact (ADR-0009, T-012)."""
    raise NotImplementedError("next_question is implemented in T-012")


def facts_summary(facts: CaseFacts) -> str:
    """Plain-language summary of the facts for the founder to confirm (ADR-0009, T-012)."""
    raise NotImplementedError("facts_summary is implemented in T-012")
