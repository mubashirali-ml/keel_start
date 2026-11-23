"""Shared fixtures and collection hooks (ADR-0007, ADR-0024, ADR-0025). Owned by T-001.

- Fixtures import ``launch_agents`` lazily, and fixtures that need a module another ticket
  still has to implement (``engine``, ``repo``) call ``pytest.skip`` instead of erroring.
- A test module (or test) that fails because an ADR-0025 package is not installed is
  skipped with the reason ``package X not installed (ADR-0025)``. Only the package's own
  top-level module being absent counts; a bad import from an installed package still fails.
- Tests marked ``postgres`` run only when ``LAUNCH_TEST_POSTGRES_URL`` is set.
- No fixture touches the network or reads the real environment.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import date
from decimal import Decimal

import pytest

# import name -> pip name of the packages added by ADR-0025
ADR0025_PACKAGES: dict[str, str] = {
    "alembic": "alembic",
    "psycopg": "psycopg",
    "argon2": "argon2-cffi",
    "stripe": "stripe",
    "reportlab": "reportlab",
    "docx": "python-docx",
    "email_validator": "email-validator",
}

TODAY = date(2026, 11, 23)

# The settings map every test starts from (APP_ENV=test, all fakes, fixed today).
TEST_ENV: dict[str, str] = {
    "APP_ENV": "test",
    "LAUNCH_FAKE_SERVICES": "1",
    "LAUNCH_TODAY": TODAY.isoformat(),
    "APP_BASE_URL": "http://testserver",
    "EMAIL_FROM": "no-reply@example.com",
}


# ---------------------------------------------------------------------------------------
# ADR-0025: skip, don't error, when a newly approved package is not installed yet
# ---------------------------------------------------------------------------------------
def adr0025_package_missing(root: str) -> bool:
    """True when the top-level module ``root`` cannot be imported: it is blocked in
    ``sys.modules`` (``None``) or no finder locates it. An installed package is never missing."""
    if root in sys.modules:
        return sys.modules[root] is None
    try:
        return importlib.util.find_spec(root) is None
    except (ImportError, ValueError):
        return False


def missing_adr0025_package(exc: BaseException | None) -> str | None:
    """The pip name of the ADR-0025 package whose absence caused ``exc`` (following the
    ``__cause__`` / ``__context__`` chain), else None.

    Only a ``ModuleNotFoundError`` for exactly the package's top-level module counts, and only
    while that module really cannot be imported. A bad name imported from an installed package
    (plain ``ImportError``) or a missing submodule (``name="alembic.no_such_module"``) is a real
    bug and stays a failure."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if (isinstance(exc, ModuleNotFoundError) and exc.name in ADR0025_PACKAGES
                and adr0025_package_missing(exc.name)):
            return ADR0025_PACKAGES[exc.name]
        exc = exc.__cause__ or exc.__context__
    return None


def adr0025_skip_reason(package: str) -> str:
    return f"package {package} not installed (ADR-0025)"


class _Adr0025Module(pytest.Module):
    """A test module whose import fails only for a missing ADR-0025 package is skipped."""

    def collect(self):
        try:
            return super().collect()
        except self.CollectError as exc:
            package = missing_adr0025_package(exc.__cause__ or exc.__context__)
            if package is None:
                raise
            pytest.skip(adr0025_skip_reason(package), allow_module_level=True)


def pytest_pycollect_makemodule(module_path, parent):
    if module_path.name == "__init__.py":
        return None  # packages: default handling
    return _Adr0025Module.from_parent(parent, path=module_path)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.excinfo is not None and report.failed:
        package = missing_adr0025_package(call.excinfo.value)
        if package is not None:
            report.outcome = "skipped"
            report.longrepr = (str(item.path), item.location[1] or 0, f"Skipped: {adr0025_skip_reason(package)}")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("LAUNCH_TEST_POSTGRES_URL"):
        return
    skip = pytest.mark.skip(reason="LAUNCH_TEST_POSTGRES_URL is not set (PostgreSQL tests run in CI)")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)


def _skip_if_stub(call, what: str):
    try:
        return call()
    except NotImplementedError as exc:
        pytest.skip(f"{what} is still a stub: {exc}")


# ---------------------------------------------------------------------------------------
# ADR-0007 fixtures
# ---------------------------------------------------------------------------------------
@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def sample_facts():
    """Wyoming LLC; Alice Chen 60 % 48/12; Bob Diaz 40 % with no vesting stated; incorporation
    2026-12-01; bookkeeping software for small bakeries."""
    from launch_agents.domain import CaseFacts, EntityType, Founder

    return CaseFacts(
        business_description="bookkeeping software for small bakeries",
        founders=[
            Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("60"),
                    vesting_months=48, cliff_months=12),
            Founder(id="f2", name="Bob Diaz", email="bob@example.com", equity_percent=Decimal("40")),
        ],
        entity_type=EntityType.LLC,
        state="WY",
        incorporation_date=date(2026, 12, 1),
    )


@pytest.fixture
def fake_llm():
    from launch_agents.llm import FakeLLM

    return FakeLLM()


@pytest.fixture
def fake_domain_checker():
    from launch_agents.ports import FakeDomainChecker

    return FakeDomainChecker()


@pytest.fixture
def fake_site_host():
    from launch_agents.ports import FakeSiteHost

    return FakeSiteHost()


# ---------------------------------------------------------------------------------------
# ADR-0024 fixtures
# ---------------------------------------------------------------------------------------
@pytest.fixture
def settings(tmp_path):
    """Test settings: ``TEST_ENV`` plus a SQLite file in ``tmp_path``. Change one value with
    ``settings.model_copy(update={...})``."""
    from launch_agents.config import load_settings

    db = (tmp_path / "test.db").as_posix()
    return load_settings({**TEST_ENV, "LAUNCH_DB_URL": f"sqlite:///{db}"})


@pytest.fixture
def engine(settings):
    """A fresh SQLite file migrated to head (skips while persistence is a stub, T-005)."""
    from launch_agents.persistence.engine import create_db_engine, init_db

    eng = _skip_if_stub(lambda: create_db_engine(settings.db_url), "persistence.engine (T-005)")
    _skip_if_stub(lambda: init_db(eng), "persistence.engine.init_db (T-005)")
    yield eng
    eng.dispose()


@pytest.fixture
def repo(engine):
    """The case ``Repository`` on ``engine`` (skips while it is a stub, T-005)."""
    from launch_agents.persistence.repository import Repository

    repository = Repository(engine)
    _skip_if_stub(lambda: repository.list_cases([]), "persistence.repository (T-005)")
    return repository


@pytest.fixture
def inline_jobs():
    from launch_agents.ports import InlineJobRunner

    return InlineJobRunner()


@pytest.fixture
def fake_mailer():
    from launch_agents.ports import RecordingMailer

    return RecordingMailer()


@pytest.fixture
def fake_notifier():
    from launch_agents.ports import RecordingNotifier

    return RecordingNotifier()


@pytest.fixture
def fake_payments(settings):
    from launch_agents.ports import FakePaymentGateway

    return FakePaymentGateway(settings)


@pytest.fixture
def entitlements_free():
    from launch_agents.domain import PlanId
    from launch_agents.ports import StaticEntitlements

    return StaticEntitlements(PlanId.FREE)


@pytest.fixture
def entitlements_launch():
    from launch_agents.domain import PlanId
    from launch_agents.ports import StaticEntitlements

    return StaticEntitlements(PlanId.LAUNCH)


@pytest.fixture
def entitlements_team():
    from launch_agents.domain import PlanId
    from launch_agents.ports import StaticEntitlements

    return StaticEntitlements(PlanId.TEAM)


@pytest.fixture
def sample_user():
    """Alice Chen, verified."""
    from datetime import datetime, timezone

    from launch_agents.domain import User

    created = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
    return User(id="usr_alice000001", email="alice@example.com", full_name="Alice Chen",
                email_verified_at=created, created_at=created)


@pytest.fixture
def request_ctx():
    """Factory: ``request_ctx(user=None, **fields)`` -> ``RequestContext``."""
    from launch_agents.domain import RequestContext

    def make(user=None, **fields):
        values = {"request_id": "req-test-0001", "ip": "127.0.0.1", "user_agent": "pytest", **fields}
        return RequestContext(user=user, **values)

    return make


@pytest.fixture
def system_access():
    """Factory: ``system_access(case_id, plan=PlanId.LAUNCH)`` -> ``CaseAccess.system(...)``."""
    from launch_agents.domain import CaseAccess, Entitlements, PlanId

    def make(case_id: str, plan=PlanId.LAUNCH, *, billing_user_id: str | None = None):
        return CaseAccess.system(case_id, Entitlements.for_plan(plan), billing_user_id=billing_user_id)

    return make
