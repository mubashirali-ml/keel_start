"""Engine creation and migrations (ADR-0027). Owned by T-005.

``create_db_engine`` builds a SQLAlchemy engine for the two supported databases:

- SQLite (development and tests): ``check_same_thread=False`` so the engine can be shared by
  the API's worker threads, ``PRAGMA foreign_keys=ON`` on every new connection (the
  cascades of ADR-0027 depend on it), and ``StaticPool`` for the in-memory ``sqlite://`` URL
  so every checkout sees the same database.
- PostgreSQL through psycopg 3 (production): ``pool_pre_ping=True`` and a 15 s
  ``statement_timeout`` set on every connection. ``postgresql://`` and ``postgres://`` URLs
  are normalised to ``postgresql+psycopg://`` (the only PostgreSQL driver of ADR-0025).

``init_db`` runs the Alembic migrations to head programmatically (dev and tests; production
runs ``alembic upgrade head`` as a release step). ``schema_is_current`` is the readiness check
of ADR-0034. ``alembic`` is imported lazily so importing this module stays cheap.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

__all__ = ["STATEMENT_TIMEOUT_MS", "create_db_engine", "init_db", "schema_is_current"]

STATEMENT_TIMEOUT_MS = 15_000  # PostgreSQL statement_timeout (ADR-0027)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"
_MIGRATIONS = _REPO_ROOT / "migrations"


def _normalise(url: str | URL) -> URL:
    u = make_url(url)
    if u.drivername in ("postgresql", "postgres", "postgresql+psycopg2"):
        u = u.set(drivername="postgresql+psycopg")
    return u


def _sqlite_foreign_keys_on(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(url: str) -> Engine:
    """SQLite: ``check_same_thread=False``, ``PRAGMA foreign_keys=ON``, ``sqlite://`` uses
    ``StaticPool``; PostgreSQL (psycopg): ``pool_pre_ping=True``, 15 s ``statement_timeout`` (T-005)."""
    u = _normalise(url)
    backend = u.get_backend_name()
    if backend == "sqlite":
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if u.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool
        engine = create_engine(u, **kwargs)
        event.listen(engine, "connect", _sqlite_foreign_keys_on)
        return engine
    if backend == "postgresql":
        return create_engine(
            u,
            pool_pre_ping=True,
            connect_args={"options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"},
        )
    raise ValueError(f"unsupported database URL {u.render_as_string(hide_password=True)!r}: "
                     "use sqlite:/// or postgresql+psycopg:// (ADR-0027)")


def _alembic_config():
    from alembic.config import Config

    if _ALEMBIC_INI.is_file():
        config = Config(str(_ALEMBIC_INI))
    else:  # pragma: no cover - a layout without alembic.ini
        config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.attributes["configure_logger"] = False  # never reconfigure the app's logging
    return config


def _script_heads() -> set[str]:
    from alembic.script import ScriptDirectory

    return set(ScriptDirectory.from_config(_alembic_config()).get_heads())


def init_db(engine: Engine) -> None:
    """``alembic upgrade head`` programmatically; idempotent. Dev and tests only (T-005)."""
    from alembic import command

    config = _alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def schema_is_current(engine: Engine) -> bool:
    """True when the database is at the latest migration (readiness, ADR-0034) (T-005).

    False on an empty database, one behind head, or one that cannot be reached."""
    from alembic.migration import MigrationContext

    try:
        with engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
    except SQLAlchemyError:
        return False
    return bool(current) and current == _script_heads()
