"""Engine creation and migrations (ADR-0027). Owned by T-005.

``alembic`` and ``psycopg`` are imported lazily inside the implementation.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine

__all__ = ["create_db_engine", "init_db", "schema_is_current"]


def create_db_engine(url: str) -> Engine:
    """SQLite: ``check_same_thread=False``, ``PRAGMA foreign_keys=ON``, ``sqlite://`` uses
    ``StaticPool``; PostgreSQL (psycopg): ``pool_pre_ping=True``, 15 s ``statement_timeout`` (T-005)."""
    raise NotImplementedError("create_db_engine is implemented in T-005")


def init_db(engine: Engine) -> None:
    """``alembic upgrade head`` programmatically; idempotent. Dev and tests only (T-005)."""
    raise NotImplementedError("init_db is implemented in T-005")


def schema_is_current(engine: Engine) -> bool:
    """True when the database is at the latest migration (readiness, ADR-0034) (T-005)."""
    raise NotImplementedError("schema_is_current is implemented in T-005")
