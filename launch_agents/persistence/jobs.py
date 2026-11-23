"""The jobs table and worker heartbeats: insert, claim (SKIP LOCKED on PostgreSQL, a conditional update on SQLite), outcomes, lease expiry and listing (ADR-0028). Owned by T-030.

T-001 provides the class and its constructor; T-030 defines the methods (the ADRs name this
repository by responsibility only).
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["JobsRepository"]


class JobsRepository:
    """The jobs table and worker heartbeats: insert, claim (SKIP LOCKED on PostgreSQL, a conditional update on SQLite), outcomes, lease expiry and listing (ADR-0028)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
