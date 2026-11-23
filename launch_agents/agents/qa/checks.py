"""QA Agent: deterministic site checks plus one LLM requirements review (ADR-0015). Owned by T-009."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ...domain.messages import ChatMessage
from ...domain.types import CaseFacts
from ...domain.website import QaCheckResult, QaIssue, QaReport, SiteBundle
from ...llm.provider import LLMProvider

__all__ = ["QaLlmReview", "deterministic_checks", "qa_summary_message", "run_qa"]


class QaLlmReview(BaseModel):
    """Output of the ``qa.review`` task (ADR-0010)."""

    issues: list[QaIssue]


def deterministic_checks(bundle: SiteBundle, facts: CaseFacts) -> list[QaCheckResult]:
    """The nine deterministic checks of ADR-0015, in ``QaCheckId`` order (T-009)."""
    raise NotImplementedError("deterministic_checks is implemented in T-009")


def run_qa(bundle: SiteBundle, facts: CaseFacts, llm: LLMProvider, *, round: int = 0, now: datetime) -> QaReport:
    """All ten checks (the tenth is ``qa.review``); passed iff no error issue (T-009)."""
    raise NotImplementedError("run_qa is implemented in T-009")


def qa_summary_message(report: QaReport) -> ChatMessage:
    """The QA Agent's ``qa_report`` chat message for one report (T-009)."""
    raise NotImplementedError("qa_summary_message is implemented in T-009")
