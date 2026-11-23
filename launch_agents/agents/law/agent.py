"""The Law Agent: legal Q&A and the request to draft documents (ADR-0009, ADR-0014). Owned by T-006."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ...domain.messages import AgentId
from ..base import AgentContext, AgentReply

__all__ = ["LawAgent", "LawIntent"]


class LawIntent(BaseModel):
    """Output of the ``law.intent`` task (ADR-0010)."""

    intent: Literal["question", "draft_documents"]
    topic: str | None


class LawAgent:
    """Specialist (``AgentId.LAW``): answers legal questions (``law.answer``) and returns
    ``DraftDocuments`` / ``OpenView("legal")`` actions; never raises for LLM failures."""

    agent_id = AgentId.LAW

    def handle(self, ctx: AgentContext) -> AgentReply:
        raise NotImplementedError("LawAgent.handle is implemented in T-006")
