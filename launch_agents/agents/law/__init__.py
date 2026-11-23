"""Law Agent (ADR-0009, ADR-0014). Owned by T-006."""

from .agent import LawAgent, LawIntent
from .documents import draft_documents
from .issues import spot_legal_issues

__all__ = ["LawAgent", "LawIntent", "draft_documents", "spot_legal_issues"]
