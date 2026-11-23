"""Registration Guide Agent (ADR-0016). Owned by T-010."""

from __future__ import annotations

from ...domain.guide import RegistrationGuide
from ...domain.messages import AgentId
from ...domain.types import CaseFacts
from ..base import AgentContext, AgentReply

__all__ = ["GuideAgent", "build_guide"]


class GuideAgent:
    """Specialist (``AgentId.GUIDE``): explains steps (task ``guide.explain``), returns ``OpenView("guide")``."""

    agent_id = AgentId.GUIDE

    def handle(self, ctx: AgentContext) -> AgentReply:
        raise NotImplementedError("GuideAgent.handle is implemented in T-010")


def build_guide(facts: CaseFacts, *, chosen_domain: str | None, deployed_url: str | None) -> RegistrationGuide:
    """Full guide for DE/WY from curated data, a generic checklist elsewhere;
    ``FactsNotReadyError`` without a state and entity type (ADR-0016, T-010)."""
    raise NotImplementedError("build_guide is implemented in T-010")

