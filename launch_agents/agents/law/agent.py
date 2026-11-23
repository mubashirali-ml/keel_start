"""The Law Agent: legal Q&A and the request to draft documents (ADR-0009, ADR-0014). Owned by T-006.

One turn:

1. Spot issues deterministically (``spot_legal_issues``) and store them in
   ``state.legal_issues``.
2. Classify the founder's message (``law.intent`` -> ``LawIntent``).
3. A draft request returns ``DraftDocuments`` + ``OpenView("legal")`` when the facts are
   locked, otherwise explains that the Manager must confirm the facts first; both hand the
   chat back to the Manager.
4. A question is answered with ``law.answer``; the spotted issues relevant to the topic
   (every warning, plus the info issues for that topic) are listed under the answer.

Every message ends with ``LEGAL_NOTICE``. ``LLMOutputError`` becomes a friendly apology.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from ...domain.constants import LEGAL_NOTICE
from ...domain.errors import LLMOutputError
from ...domain.helpers import deadline_83b
from ...domain.messages import AgentId, ChatMessage, DraftDocuments, OpenView, SuggestedReply, agent_message
from ...domain.state import CaseState, LegalIssue
from ...domain.types import CaseFacts, EntityType
from ...llm.provider import LLMRequest
from ..base import AgentContext, AgentReply
from . import prompts
from .issues import format_date, resolved_vesting, spot_legal_issues
from .topics import normalise_topic

__all__ = ["APOLOGY", "LawAgent", "LawIntent", "relevant_issues", "with_notice"]

APOLOGY = (
    "Sorry, I couldn't put together a legal answer just now because the AI service didn't respond "
    "properly. Please ask me again in a moment."
)

# Info-level issues shown with an answer on these topics (warnings are always shown).
_TOPIC_ISSUES: dict[str, frozenset[str]] = {
    "vesting": frozenset({"unequal_vesting", "no_cliff"}),
}


class LawIntent(BaseModel):
    """Output of the ``law.intent`` task (ADR-0010)."""

    intent: Literal["question", "draft_documents"]
    topic: str | None


def with_notice(text: str) -> str:
    """``text`` followed by ``LEGAL_NOTICE`` (a notice the model already wrote is not doubled)."""
    body = text.strip()
    while body.endswith(LEGAL_NOTICE):
        body = body[: -len(LEGAL_NOTICE)].rstrip()
    return f"{body}\n\n{LEGAL_NOTICE}" if body else LEGAL_NOTICE


def relevant_issues(issues: list[LegalIssue], topic: str) -> list[LegalIssue]:
    """Every warning, plus the info issues that belong to ``topic`` (all of them for ``general``)."""
    wanted = _TOPIC_ISSUES.get(topic, frozenset())
    return [i for i in issues if i.severity == "warning" or topic == "general" or i.code in wanted]


def _answer_context(text: str, topic: str, facts: CaseFacts, issues: list[LegalIssue]) -> dict[str, Any]:
    founders = []
    for founder in facts.founders:
        vesting, cliff = resolved_vesting(founder)
        founders.append({
            "name": founder.name,
            "equity_percent": format(founder.equity_percent.normalize(), "f"),
            "vesting_months": vesting,
            "cliff_months": cliff,
        })
    return {
        "text": text,
        "topic": topic,
        "entity_type": facts.entity_type.value if facts.entity_type else None,
        "state": facts.state,
        "founders": founders,
        "issues": [i.message for i in issues],
        "deadline_83b": deadline_83b(facts.incorporation_date).isoformat() if facts.incorporation_date else None,
    }


class LawAgent:
    """Specialist (``AgentId.LAW``): answers legal questions (``law.answer``) and returns
    ``DraftDocuments`` / ``OpenView("legal")`` actions; never raises for LLM failures."""

    agent_id = AgentId.LAW

    def handle(self, ctx: AgentContext) -> AgentReply:
        issues = spot_legal_issues(ctx.facts, ctx.state, ctx.today)
        state = ctx.state.model_copy(update={"legal_issues": issues})
        try:
            intent = ctx.llm.complete_json(
                LLMRequest(task="law.intent", messages=prompts.intent_messages(ctx.founder_text),
                           context={"text": ctx.founder_text}),
                LawIntent,
            )
            if intent.intent == "draft_documents":
                return self._draft(ctx, state, issues)
            return self._answer(ctx, state, issues, normalise_topic(intent.topic, ctx.founder_text))
        except LLMOutputError:
            return AgentReply(messages=[self._say(APOLOGY)], state=state, hand_back=False)

    # -- replies --------------------------------------------------------------------------
    def _say(self, text: str, suggested: list[SuggestedReply] | None = None) -> ChatMessage:
        return agent_message(self.agent_id, with_notice(text), suggested_replies=suggested)

    def _answer(self, ctx: AgentContext, state: CaseState, issues: list[LegalIssue], topic: str) -> AgentReply:
        shown = relevant_issues(issues, topic)
        context = _answer_context(ctx.founder_text, topic, ctx.facts, shown)
        answer = ctx.llm.complete(
            LLMRequest(task="law.answer", messages=prompts.answer_messages(context, ctx.history), context=context)
        ).strip()
        if not answer:
            raise LLMOutputError("The AI service returned an empty answer.", details={"task": "law.answer"})
        text = answer
        if shown:
            text += "\n\n**What I noticed in your case:**\n" + "\n".join(f"- {i.message}" for i in shown)
        suggested = (
            [SuggestedReply(label="Draft our documents", text="Please draft our founding documents.")]
            if state.facts_locked else None
        )
        return AgentReply(messages=[self._say(text, suggested)], state=state, hand_back=False)

    def _draft(self, ctx: AgentContext, state: CaseState, issues: list[LegalIssue]) -> AgentReply:
        facts = ctx.facts
        if not state.facts_locked:
            text = (
                "I can draft your founding documents as soon as your case facts are confirmed. The Manager "
                "first needs to confirm the facts with you (founders, equity split, vesting, entity type, "
                "state and incorporation date), so that every document and share count matches. I'm handing "
                "you back to the Manager to review and confirm them; then ask me again."
            )
            return AgentReply(messages=[self._say(text)], state=state, hand_back=True)

        summary = (
            "the Operating Agreement Summary" if facts.entity_type == EntityType.LLC else "the Bylaws Summary"
        )
        text = (
            "Your facts are confirmed, so I'm preparing your founding documents now: the Founder IP "
            f"Assignment Agreement, {summary} and an IRS 83(b) election for each founder. Share counts come "
            "straight from your cap table. They will open in the Legal view for every founder to review and "
            "sign; details I don't know, like addresses, stay as placeholders for you to fill in."
        )
        if facts.incorporation_date:
            text += (f" Remember: each 83(b) must reach the IRS by "
                     f"**{format_date(deadline_83b(facts.incorporation_date))}**.")
        warnings = [i for i in issues if i.severity == "warning"]
        if warnings:
            text += "\n\n**Before you sign:**\n" + "\n".join(f"- {i.message}" for i in warnings)
        return AgentReply(
            messages=[self._say(text)],
            state=state,
            actions=[DraftDocuments(), OpenView(view="legal")],
            hand_back=True,
        )
