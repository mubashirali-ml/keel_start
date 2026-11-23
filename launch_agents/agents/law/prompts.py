"""Prompts for the Law Agent's LLM tasks (ADR-0010: prompts live next to the agent). T-006.

Every input the agent puts into ``LLMRequest.context`` also appears in the prompt text, so a
real model sees exactly what the fake handler reads.
"""

from __future__ import annotations

from typing import Any, Sequence

from ...domain.messages import ChatMessage, MessageKind, MessageRole
from ...llm.provider import LLMMessage
from .topics import TOPICS

__all__ = ["ANSWER_SYSTEM_PROMPT", "INTENT_SYSTEM_PROMPT", "answer_messages", "intent_messages"]

INTENT_SYSTEM_PROMPT = (
    "You are the Law Agent in an app that helps US startup founders form their company. "
    "Classify the founder's latest message.\n"
    "- intent \"draft_documents\" when they ask you to draft, prepare or produce the founding "
    "documents or paperwork (IP assignment, bylaws / operating agreement summary, 83(b) forms).\n"
    "- intent \"question\" for everything else.\n"
    f"topic is one of {', '.join(TOPICS)} for a question (entity_choice = LLC vs C-Corp; "
    "83b = the IRS 83(b) election), or null for a draft request.\n"
    "Answer with a JSON object {\"intent\": ..., \"topic\": ...} and nothing else."
)

ANSWER_SYSTEM_PROMPT = (
    "You are the Law Agent in an app that helps US startup founders form their company. "
    "You explain the legal side in plain, friendly English: LLC vs Delaware C-Corp, choice of "
    "state, liability protection, operating agreement basics, tax treatment, founder vesting "
    "and the IRS 83(b) election.\n"
    "Rules:\n"
    "- Answer the founder's question in one or two short paragraphs, using the facts of their "
    "case below (entity type, state, founders, vesting, 83(b) deadline) where relevant.\n"
    "- Never invent facts, numbers or share counts that are not given below.\n"
    "- The app lists the spotted issues and adds the not-legal-advice notice after your answer, "
    "so do not repeat either. No JSON, no code, no headings; **bold** and short lists are fine."
)


def intent_messages(text: str) -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content=INTENT_SYSTEM_PROMPT),
        LLMMessage(role="user", content=f"Founder message:\n{text}"),
    ]


def _case_block(context: dict[str, Any]) -> str:
    lines = [
        f"Topic: {context.get('topic') or 'general'}",
        f"Entity type: {context.get('entity_type') or 'not chosen yet'}",
        f"State of formation: {context.get('state') or 'not chosen yet'}",
        f"83(b) deadline: {context.get('deadline_83b') or 'unknown (no incorporation date yet)'}",
    ]
    founders = context.get("founders") or []
    if founders:
        lines.append("Founders:")
        for f in founders:
            lines.append(
                f"- {f['name']}: {f['equity_percent']}% equity, vesting {f['vesting_months']} months, "
                f"cliff {f['cliff_months']} months"
            )
    else:
        lines.append("Founders: none given yet")
    issues = context.get("issues") or []
    if issues:
        lines.append("Issues the app spotted (shown to the founder after your answer):")
        lines.extend(f"- {message}" for message in issues)
    return "\n".join(lines)


def answer_messages(context: dict[str, Any], history: Sequence[ChatMessage]) -> list[LLMMessage]:
    """System prompt, the case facts, the recent conversation and the question."""
    messages = [
        LLMMessage(role="system", content=ANSWER_SYSTEM_PROMPT),
        LLMMessage(role="system", content="Case facts:\n" + _case_block(context)),
    ]
    for message in list(history)[-8:]:
        if message.kind != MessageKind.TEXT or message.role == MessageRole.SYSTEM:
            continue
        role = "user" if message.role == MessageRole.FOUNDER else "assistant"
        messages.append(LLMMessage(role=role, content=message.content))
    messages.append(LLMMessage(role="user", content=str(context.get("text", ""))))
    return messages
