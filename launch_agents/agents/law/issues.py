"""Deterministic legal issue spotting (ADR-0009). Owned by T-006."""

from __future__ import annotations

from datetime import date

from ...domain.state import CaseState, LegalIssue
from ...domain.types import CaseFacts

__all__ = ["spot_legal_issues"]


def spot_legal_issues(facts: CaseFacts, state: CaseState, today: date) -> list[LegalIssue]:
    """Info/warning issues the Law Agent points out (e.g. 83(b) deadline close) (T-006)."""
    raise NotImplementedError("spot_legal_issues is implemented in T-006")
