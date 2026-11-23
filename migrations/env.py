"""Alembic environment (ADR-0027).

The database URL comes, in order, from: a connection handed over programmatically in
``config.attributes["connection"]`` (``init_db``, tests); ``sqlalchemy.url`` set on the
config (``-x``-free programmatic use); else ``load_settings().db_url``. ``alembic.ini`` holds
no URL, so credentials never live in a file.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from launch_agents.persistence.tables import metadata

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata


def _database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    from launch_agents.config import load_settings

    return load_settings().db_url


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,  # SQLite needs batch mode for later ALTERs
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=_database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            _configure(connection=conn)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
