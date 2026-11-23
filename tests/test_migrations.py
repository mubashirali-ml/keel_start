"""T-005: ``create_db_engine`` options, ``init_db`` / ``schema_is_current`` and the Alembic
migrations (upgrade -> downgrade -> upgrade, empty autogenerate diff against ``tables.py``),
on SQLite and, when ``LAUNCH_TEST_POSTGRES_URL`` is set, on PostgreSQL (marker ``postgres``)."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import event, inspect, text
from sqlalchemy.pool import StaticPool

from launch_agents.persistence.engine import STATEMENT_TIMEOUT_MS, create_db_engine, init_db, schema_is_current
from launch_agents.persistence.tables import TABLE_NAMES, metadata

REPO_ROOT = Path(__file__).resolve().parents[1]


def _config(connection) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.attributes["configure_logger"] = False
    config.attributes["connection"] = connection
    return config


def _head() -> str:
    return ScriptDirectory.from_config(_config(None)).get_current_head()


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=pytest.mark.postgres)])
def db_engine(request, tmp_path):
    if request.param == "sqlite":
        eng = create_db_engine(f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}")
    else:
        eng = create_db_engine(os.environ["LAUNCH_TEST_POSTGRES_URL"])
        _downgrade(eng)  # start from an empty schema
    yield eng
    if request.param == "postgres":
        _downgrade(eng)
    eng.dispose()


def _upgrade(engine) -> None:
    with engine.begin() as conn:
        command.upgrade(_config(conn), "head")


def _downgrade(engine) -> None:
    with engine.begin() as conn:
        command.downgrade(_config(conn), "base")


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def _diff(engine) -> list:
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True, "target_metadata": metadata})
        return compare_metadata(context, metadata)


# ---------------------------------------------------------------------------------------
# AC 2 / 3: migrations
# ---------------------------------------------------------------------------------------
def test_upgrade_downgrade_upgrade(db_engine):
    assert _tables(db_engine) == set()
    _upgrade(db_engine)
    assert _tables(db_engine) == set(TABLE_NAMES)
    _downgrade(db_engine)
    assert _tables(db_engine) == set()
    assert schema_is_current(db_engine) is False
    _upgrade(db_engine)
    assert _tables(db_engine) == set(TABLE_NAMES)
    assert schema_is_current(db_engine) is True


def test_autogenerate_diff_against_tables_py_is_empty(db_engine):
    init_db(db_engine)
    assert _diff(db_engine) == []


def test_init_db_runs_to_head_and_is_idempotent(db_engine):
    assert schema_is_current(db_engine) is False  # empty database
    init_db(db_engine)
    assert schema_is_current(db_engine) is True
    with db_engine.connect() as conn:
        assert MigrationContext.configure(conn).get_current_revision() == _head() == "0001_initial"
        conn.execute(text("INSERT INTO worker_heartbeats (worker_id, last_seen_at) "
                          "VALUES ('w1', CURRENT_TIMESTAMP)"))
        conn.commit()
    init_db(db_engine)  # second run: no-op, data kept
    assert schema_is_current(db_engine) is True
    with db_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM worker_heartbeats")).scalar_one() == 1
    assert _tables(db_engine) == set(TABLE_NAMES)


def test_init_db_on_in_memory_sqlite_keeps_the_schema_across_checkouts():
    eng = create_db_engine("sqlite://")
    try:
        assert isinstance(eng.pool, StaticPool)
        assert schema_is_current(eng) is False
        init_db(eng)
        assert schema_is_current(eng) is True and _tables(eng) == set(TABLE_NAMES)
    finally:
        eng.dispose()


def test_schema_is_current_is_false_when_the_database_cannot_be_reached(tmp_path):
    missing_dir = tmp_path / "no" / "such" / "dir"
    eng = create_db_engine(f"sqlite:///{(missing_dir / 'x.db').as_posix()}")
    try:
        assert schema_is_current(eng) is False
    finally:
        eng.dispose()


# ---------------------------------------------------------------------------------------
# AC 1: engine options
# ---------------------------------------------------------------------------------------
def test_sqlite_file_engine_enables_foreign_keys_on_every_connection_and_crosses_threads(tmp_path):
    eng = create_db_engine(f"sqlite:///{(tmp_path / 'fk.db').as_posix()}")
    try:
        assert not isinstance(eng.pool, StaticPool)
        held = [eng.connect() for _ in range(3)]  # three distinct pooled DBAPI connections
        try:
            assert [c.exec_driver_sql("PRAGMA foreign_keys").scalar() for c in held] == [1, 1, 1]
        finally:
            for c in held:
                c.close()
        conn = eng.connect()
        result: dict = {}

        def use_elsewhere():  # check_same_thread=False: a connection may be used by another thread
            try:
                result["fk"] = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
            except Exception as exc:  # pragma: no cover - reported below
                result["error"] = exc

        t = threading.Thread(target=use_elsewhere)
        t.start()
        t.join()
        conn.close()
        assert result == {"fk": 1}
    finally:
        eng.dispose()


def test_in_memory_sqlite_uses_static_pool_and_foreign_keys():
    eng = create_db_engine("sqlite://")
    try:
        assert isinstance(eng.pool, StaticPool)
        with eng.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            conn.exec_driver_sql("CREATE TABLE t (x INTEGER)")
        with eng.connect() as conn:  # same database on the next checkout
            assert "t" in inspect(conn).get_table_names()
    finally:
        eng.dispose()


class _Captured(Exception):
    pass


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://app:secret@db.invalid:5432/launch",
    "postgresql://app:secret@db.invalid:5432/launch",
    "postgres://app:secret@db.invalid:5432/launch",
])
def test_postgres_engine_uses_psycopg_pre_ping_and_statement_timeout(url):
    eng = create_db_engine(url)  # no connection is made here
    captured: dict = {}

    @event.listens_for(eng, "do_connect")
    def capture(dialect, conn_rec, cargs, cparams):
        captured.update(cparams)
        raise _Captured()

    try:
        assert eng.dialect.name == "postgresql" and eng.dialect.driver == "psycopg"
        assert eng.pool._pre_ping is True
        with pytest.raises(_Captured):
            eng.connect()
        assert captured["options"] == f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"
        assert STATEMENT_TIMEOUT_MS == 15_000
        assert captured["host"] == "db.invalid" and captured["dbname"] == "launch"
    finally:
        eng.dispose()


def test_unsupported_database_url_is_rejected():
    with pytest.raises(ValueError, match="unsupported database URL"):
        create_db_engine("mysql+pymysql://u:p@localhost/db")


@pytest.mark.postgres
def test_postgres_connection_has_the_statement_timeout():
    eng = create_db_engine(os.environ["LAUNCH_TEST_POSTGRES_URL"])
    try:
        with eng.connect() as conn:
            assert conn.execute(text("SHOW statement_timeout")).scalar_one() == "15s"
    finally:
        eng.dispose()
