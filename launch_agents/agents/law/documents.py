"""Founding-document drafting (ADR-0014). Owned by T-006."""

from __future__ import annotations

from datetime import date

from ...domain.cap_table import CapTable
from ...domain.documents import DraftDocument
from ...domain.types import CaseFacts

__all__ = ["draft_documents"]


def draft_documents(facts: CaseFacts, cap_table: CapTable, today: date) -> list[DraftDocument]:
    """IP assignment, bylaws / operating agreement summary and one 83(b) per founder, as
    Markdown starting and ending with ``LEGAL_NOTICE``; share counts only from ``cap_table``
    (ADR-0014, T-006)."""
    raise NotImplementedError("draft_documents is implemented in T-006")
