"""Metadata-only read models for the admin area; never chat, document or website content (ADR-0034, ADR-0038). Owned by T-038.

T-001 provides the class and its constructor; T-038 defines the methods (the ADRs name this
repository by responsibility only).
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["AdminQueries"]


class AdminQueries:
    """Metadata-only read models for the admin area; never chat, document or website content (ADR-0034, ADR-0038)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
