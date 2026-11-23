"""Website content generation, revision and fixing (ADR-0015). Owned by T-008."""

from __future__ import annotations

from ...domain.types import CaseFacts
from ...domain.website import QaIssue, SiteContent
from ...llm.provider import LLMProvider

__all__ = ["fix_content", "generate_content", "revise_content"]


def generate_content(facts: CaseFacts, llm: LLMProvider) -> SiteContent:
    """First draft of the site content (task ``website.generate``, T-008)."""
    raise NotImplementedError("generate_content is implemented in T-008")


def revise_content(content: SiteContent, change_request: str, facts: CaseFacts, llm: LLMProvider) -> SiteContent:
    """Apply a founder's change request (task ``website.revise``, T-008)."""
    raise NotImplementedError("revise_content is implemented in T-008")


def fix_content(content: SiteContent, issues: list[QaIssue], facts: CaseFacts, llm: LLMProvider) -> SiteContent:
    """Fix the QA error issues (task ``website.fix``, T-008)."""
    raise NotImplementedError("fix_content is implemented in T-008")
