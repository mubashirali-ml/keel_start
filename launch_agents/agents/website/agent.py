"""The Website Agent: understands build / change / deploy requests (ADR-0009, ADR-0015). Owned by T-008."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ...domain.messages import AgentId
from ...domain.types import WebsitePatch
from ..base import AgentContext, AgentReply

__all__ = ["WebsiteAgent", "WebsiteIntent"]


class WebsiteIntent(BaseModel):
    """Output of the ``website.intent`` task (ADR-0010)."""

    intent: Literal["build", "change", "deploy", "question"]
    change_request: str | None
    override_qa: bool
    requirements: WebsitePatch | None


class WebsiteAgent:
    """Specialist (``AgentId.WEBSITE``): returns ``BuildWebsite`` / ``DeployWebsite`` /
    ``OpenView("website")`` actions; the build itself runs in the pipeline (T-013)."""

    agent_id = AgentId.WEBSITE

    def handle(self, ctx: AgentContext) -> AgentReply:
        raise NotImplementedError("WebsiteAgent.handle is implemented in T-008")
