"""Read and delete queries for the data export and account deletion (ADR-0034). Owned by T-037.

T-001 provides the class and its constructor; T-037 defines the methods (the ADRs name this
repository by responsibility only).
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["PrivacyQueries"]


class PrivacyQueries:
    """Read and delete queries for the data export and account deletion (ADR-0034)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
