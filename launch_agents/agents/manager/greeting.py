"""The Manager's first message in every new company (ADR-0009, ADR-0039). Implemented in T-001."""

from __future__ import annotations

from ...domain.constants import BRAND_NAME
from ...domain.messages import AgentId, ChatMessage, MessageKind, SuggestedReply, agent_message

__all__ = ["GREETING_SUGGESTIONS", "manager_greeting"]

GREETING_SUGGESTIONS: tuple[SuggestedReply, ...] = (
    SuggestedReply(label="I want to start an LLC", text="I want to start an LLC"),
    SuggestedReply(label="Help me choose LLC or C-Corp", text="Help me choose between an LLC and a C-Corp"),
    SuggestedReply(label="Find a company name", text="Help me find a company name"),
)


def manager_greeting(brand_name: str = BRAND_NAME) -> ChatMessage:
    """Fixed greeting: the Manager introduces itself ("the Manager at {brand}") and the specialists."""
    content = (
        f"Hi, I'm the Manager at {brand_name}. I'll guide you through launching your company "
        "and bring in the right specialist when you need one:\n\n"
        "- **Law Agent**: answers legal questions and drafts your founding documents\n"
        "- **Name Agent**: suggests company names and checks .com, .co and .io domains\n"
        "- **Website Agent**: builds your website, and the **QA Agent** checks it before it goes live\n"
        "- **Registration Guide Agent**: walks you through filing with your state, step by step\n\n"
        "To start, tell me what your company does and who the founders are."
    )
    return agent_message(
        AgentId.MANAGER,
        content,
        kind=MessageKind.TEXT,
        suggested_replies=list(GREETING_SUGGESTIONS),
    )
