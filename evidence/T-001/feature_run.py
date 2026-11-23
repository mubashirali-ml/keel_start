"""T-001 feature run: the foundation used the way later tickets will use it. No network.

Run: bash scripts/py.sh evidence/T-001/feature_run.py   (recorded by scripts/record_run.sh T-001)
Prints the real inputs and outputs and asserts the key results; exits non-zero on failure.
"""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import launch_agents  # noqa: E402
from launch_agents.config import ConfigError, load_settings  # noqa: E402
from launch_agents.domain import (  # noqa: E402
    AgentId,
    BillingInterval,
    CaseAccess,
    CaseFacts,
    Actor,
    EmailTemplate,
    Entitlements,
    EntityType,
    FactsPatch,
    Feature,
    Founder,
    FounderPatch,
    MemberRole,
    Membership,
    Permission,
    PlanId,
    PlanRequiredError,
    RetryableJobError,
    deadline_83b,
    days_until,
    document_sha256,
    apply_patch,
    handoff_message,
)
from launch_agents.llm import FakeLLM, LLMMessage, LLMRequest, get_llm, usage_sink  # noqa: E402
from launch_agents.ports import FakePaymentGateway, InlineJobRunner, RecordingMailer, fake_price_id  # noqa: E402

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 11, 23)


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def show(label: str, value) -> None:
    print(f"{label:<34} {value}")


# ---------------------------------------------------------------------------------------
section("1. Settings resolution (ADR-0021, ADR-0022); keys redacted")
ENV_MAPS = {
    "fake (no keys)": {},
    "anthropic + Haiku for Name and QA": {
        "ANTHROPIC_API_KEY": "sk-ant-demo-secret-value",
        "LLM_MODEL_NAME": "claude-haiku-5-5",
        "LLM_MODEL_QA": "claude-haiku-5-5",
    },
    "deepseek": {"DEEPSEEK_API_KEY": "sk-deepseek-demo-secret"},
    "claude_code in development": {"APP_ENV": "development", "LLM_PROVIDER": "claude_code"},
}
for label, env in ENV_MAPS.items():
    s = load_settings(env)
    provider = get_llm(s)
    print(f"\n[{label}] env={ {k: ('***' if 'KEY' in k else v) for k, v in env.items()} }")
    show("  app_env / llm_provider", f"{s.app_env.value} / {s.llm_provider} -> {type(provider).__name__}")
    show("  model_for(name.suggest)", s.model_for("name.suggest"))
    show("  model_for(qa.review)", s.model_for("qa.review"))
    show("  model_for(law.answer)", s.model_for("law.answer"))
    show("  email / payments / worker / log", f"{s.email_provider} / {s.payments_provider} / "
         f"{s.jobs_embedded_worker} / {s.log_format}")
    for value in env.values():
        if "secret" in value:
            assert value not in repr(s), "a secret leaked into repr(settings)"
assert load_settings(ENV_MAPS["fake (no keys)"]).llm_provider == "fake"
haiku = load_settings(ENV_MAPS["anthropic + Haiku for Name and QA"])
assert haiku.llm_provider == "anthropic" and haiku.model_for("qa.review") == "claude-haiku-5-5"
assert haiku.model_for("law.answer") is None
assert load_settings(ENV_MAPS["deepseek"]).llm_provider == "deepseek"
assert load_settings(ENV_MAPS["claude_code in development"]).llm_provider == "claude_code"
redacted = repr(haiku)
show("\nrepr(settings) shows", re.search(r"anthropic_api_key='[^']*'", redacted).group(0))
with_urls = load_settings({"LAUNCH_DB_URL": "postgresql+psycopg://app:S3cretPw@db/launch",
                           "LLM_BASE_URL": "https://llm-user:LlmPw99@llm.example.com/v1"})
for text in (repr(with_urls), str(with_urls)):
    assert "S3cretPw" not in text and "LlmPw99" not in text, "a URL password leaked into repr(settings)"
show("repr(settings) db_url", re.search(r"db_url='[^']*'", repr(with_urls)).group(0))
show("repr(settings) llm_base_url", re.search(r"llm_base_url='[^']*'", repr(with_urls)).group(0))
assert "db_url='postgresql+psycopg://app:***@db/launch'" in repr(with_urls)
assert with_urls.db_url.endswith("app:S3cretPw@db/launch")  # the real value is still usable

PRODUCTION = {
    "APP_ENV": "production", "LLM_PROVIDER": "claude_code", "PAYMENTS_PROVIDER": "fake",
    "EMAIL_PROVIDER": "console", "LAUNCH_DB_URL": "sqlite:///./prod.db", "SECRET_KEY": "short",
    "APP_BASE_URL": "http://app.example.com", "DEMO_MODE": "1",
    "STRIPE_SECRET_KEY": "sk_live_demo_secret", "STRIPE_WEBHOOK_SECRET": "whsec_demo_secret",
    "STRIPE_PRICE_LAUNCH_MONTHLY": "price_lm", "STRIPE_PRICE_LAUNCH_YEARLY": "price_ly",
    "STRIPE_PRICE_TEAM_YEARLY": "price_ty", "SMTP_HOST": "smtp.example.com", "EMAIL_FROM": "hello@example.com",
    "LAUNCH_CORS_ORIGINS": "https://app.example.com", "PLAN_LAUNCH_PRICE_MONTH_CENTS": "0",
}
print("\n[production with every mistake] -> ConfigError:")
try:
    load_settings(PRODUCTION)
except ConfigError as exc:
    for problem in exc.problems:
        print(f"  - {problem}")
    text = "\n".join(exc.problems)
    for needle in ("claude_code", "PAYMENTS_PROVIDER", "EMAIL_PROVIDER", "PostgreSQL", "SECRET_KEY", "APP_BASE_URL",
                   "DEMO_MODE", "STRIPE_PRICE_TEAM_MONTHLY", "SUPPORT_EMAIL", "PLAN_LAUNCH_PRICE_MONTH_CENTS"):
        assert needle in text, needle
    assert "sk_live_demo_secret" not in str(exc)
else:
    raise AssertionError("production with fakes must not load")

# ---------------------------------------------------------------------------------------
section("2. FakeLLM call inside a usage_sink (ADR-0010, ADR-0022)")
llm = FakeLLM()
llm.register("demo.task", lambda r: f"Hello {r.context['name']}, here are three name ideas.")
collected = []
with usage_sink(collected.append):
    answer = llm.complete(LLMRequest(task="demo.task", messages=[LLMMessage(role="user", content="ideas?")],
                                     context={"name": "Alice"}))
show("complete() ->", answer)
for usage in collected:
    show("usage", usage.model_dump())
assert answer.startswith("Hello Alice") and len(collected) == 1 and collected[0].provider == "fake"

# ---------------------------------------------------------------------------------------
section("3. apply_patch on sample facts (ADR-0008)")
facts = CaseFacts(
    business_description="bookkeeping software for small bakeries",
    founders=[Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("60"),
                      vesting_months=48, cliff_months=12)],
    entity_type=EntityType.LLC, state="wy", incorporation_date=date(2026, 12, 1),
)
patch = FactsPatch(founders=[FounderPatch(email="ALICE@example.com", equity_percent=Decimal("55")),
                             FounderPatch(name="Bob Diaz", email="bob@example.com", equity_percent=Decimal("45"))],
                   entity_type=EntityType.C_CORP)
show("patch", patch.model_dump(mode="json", exclude_none=True))
patched = apply_patch(facts, patch)
for f in patched.founders:
    show(f"  founder {f.id}", f"{f.name} <{f.email}> {f.equity_percent}% vesting={f.vesting_months}")
show("entity / state", f"{patched.entity_type.value} / {patched.state}")
assert [f.id for f in patched.founders] == ["f1", "f2"] and patched.founders[0].equity_percent == Decimal("55")
assert patched.state == "DE"

# ---------------------------------------------------------------------------------------
section("4. 83(b) deadline (ADR-0013)")
deadline = deadline_83b(date(2026, 12, 1))
show("incorporated 2026-12-01 -> file by", f"{deadline} ({days_until(deadline, TODAY)} days from {TODAY})")
assert deadline == date(2026, 12, 31)

# ---------------------------------------------------------------------------------------
section("5. Handoff messages (ADR-0009)")
for msg in (handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover", reason="legal question"),
            handoff_message(AgentId.LAW, AgentId.MANAGER, direction="return", reason="question answered")):
    print(json.dumps(msg.model_dump(mode="json", exclude_none=True, exclude={"suggested_replies"}), sort_keys=True))
assert handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover", reason="x").content == \
    "Manager brought in the Law Agent"

# ---------------------------------------------------------------------------------------
section("6. CaseAccess for a member and for the system (ADR-0026, ADR-0038)")
from launch_agents.access import ROLE_PERMISSIONS  # noqa: E402

bob = Actor(kind="user", user_id="usr_bob", founder_id="f2", ip="203.0.113.7", user_agent="demo", request_id="req-1")
member = CaseAccess(case_id="case_demo", actor=bob,
                    membership=Membership(case_id="case_demo", user_id="usr_bob", role=MemberRole.MEMBER,
                                          founder_id="f2", joined_at=NOW),
                    permissions=ROLE_PERMISSIONS[MemberRole.MEMBER], entitlements=Entitlements.for_plan(PlanId.FREE),
                    billing_user_id="usr_alice")
system = CaseAccess.system("case_demo", Entitlements.for_plan(PlanId.LAUNCH))
show("member permissions", sorted(p.value for p in member.permissions))
show("member audit actor", member.actor.audit_actor)
show("system permissions", sorted(p.value for p in system.permissions))
show("system audit actor", system.actor.audit_actor)
try:
    member.require_feature(Feature.ESIGN)
except PlanRequiredError as exc:
    show("Free + ESIGN ->", f"{exc.code} {exc.http_status}: {exc.message} {exc.details}")
    assert exc.details["required_plan"] == "launch"
else:
    raise AssertionError("Free must not include e-signatures")
assert Permission.MANAGE_TEAM not in member.permissions and system.permissions == frozenset(Permission)

# ---------------------------------------------------------------------------------------
section("7. InlineJobRunner: retried, then succeeds (ADR-0028)")
runner = InlineJobRunner(clock=lambda: NOW)
attempts = []


def flaky_build(job, ctx):
    attempts.append(ctx.attempt)
    if ctx.attempt < 3:
        raise RetryableJobError("The build server is busy.")
    return {"build_id": "site_demo", "attempt": ctx.attempt}


runner.register("website.build", flaky_build)
job = runner.enqueue("website.build", {"case_id": "case_demo"}, case_id="case_demo")
show("attempts seen by the handler", attempts)
show("job", job.model_dump(mode="json", include={"kind", "status", "attempts", "result", "error"}))
assert job.status.value == "succeeded" and job.attempts == 3

# ---------------------------------------------------------------------------------------
section("8. RecordingMailer dedupe (ADR-0029)")
mailer = RecordingMailer()
ids = [mailer.send(EmailTemplate.SIGNATURE_NEEDED, "bob@example.com", {"document_title": "IP Assignment"},
                   dedupe_key="sig:doc_1:1:f2") for _ in range(3)]
show("outbox ids for 3 identical sends", ids)
show("recorded emails", [(e.template.value, e.to, e.dedupe_key) for e in mailer.sent])
assert ids[0] and ids[1:] == [None, None] and len(mailer.sent) == 1

# ---------------------------------------------------------------------------------------
section("9. Fake checkout -> webhook event round trip, then Launch -> Team (ADR-0030, ADR-0038)")
settings = load_settings({"APP_ENV": "test", "APP_BASE_URL": "http://localhost:8000"})
gateway = FakePaymentGateway(settings, clock=lambda: NOW)
customer = gateway.create_customer(email="alice@example.com", user_id="usr_alice")
session = gateway.create_checkout_session(customer_id=customer,
                                          price_id=fake_price_id(PlanId.LAUNCH, BillingInterval.MONTH),
                                          user_id="usr_alice", success_url="/app/settings/billing?checkout=success",
                                          cancel_url="/pricing?checkout=cancelled")
show("checkout url", session.url)
completed = gateway.complete_checkout(session.id)
payload, signature = gateway.delivered[-1]
parsed = gateway.parse_webhook(payload, signature)
show("webhook signature header", signature.split(",")[0] + ",v1=...")
show("parsed event", parsed.model_dump(mode="json", exclude_none=True))
assert parsed == completed and session.url.startswith("http://localhost:8000/app/billing/test-checkout?session=")
changed = gateway.change_subscription_price(subscription_id=completed.subscription_id,
                                            price_id=fake_price_id(PlanId.TEAM, BillingInterval.MONTH))
parsed_change = gateway.parse_webhook(*gateway.delivered[-1])
show("price change event", parsed_change.model_dump(mode="json", include={"type", "price_id", "status"}))
show("Team monthly price amount", gateway.price_amount(parsed_change.price_id))
assert parsed_change == changed and parsed_change.price_id == "price_fake_team_monthly"
try:
    gateway.parse_webhook(payload.replace(b"usr_alice", b"usr_mallory"), signature)
except Exception as exc:  # WebhookSignatureError
    show("tampered payload ->", f"{type(exc).__name__}: {exc}")
else:
    raise AssertionError("a tampered webhook must be rejected")

# ---------------------------------------------------------------------------------------
section("10. Plans from Settings.plans() with PLAN_TEAM_AI_MESSAGES=20000 (ADR-0038)")
plans = load_settings({"PLAN_TEAM_AI_MESSAGES": "20000"}).plans()
for plan in plans.values():
    print(f"\n{plan.name} (rank {plan.rank}): ${plan.price_month_cents / 100:.0f}/month, "
          f"${plan.price_year_cents / 100:.0f}/year (yearly offered: {plan.yearly_available})")
    print(f"  companies {plan.max_companies}, AI messages {plan.llm_calls_per_month:,}, "
          f"features {[f.value for f in plan.features]}, support {plan.support.value}")
    for line in plan.highlights:
        print(f"  * {line}")
assert plans[PlanId.TEAM].llm_calls_per_month == 20000 and plans[PlanId.LAUNCH].price_month_cents == 2900
assert "20,000 AI messages a month" in plans[PlanId.TEAM].highlights

# ---------------------------------------------------------------------------------------
section("11. document_sha256 (ADR-0031)")
doc_lf = "# Founder IP Assignment Agreement\n\nAlice Chen assigns all company IP.\n"
show("sha256 (LF)", document_sha256(doc_lf))
show("sha256 (CRLF)", document_sha256(doc_lf.replace("\n", "\r\n")))
assert document_sha256(doc_lf) == document_sha256(doc_lf.replace("\n", "\r\n"))

# ---------------------------------------------------------------------------------------
section("12. Migrated tables of a temp SQLite database (ADR-0027)")
try:
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine, inspect as sa_inspect

    from launch_agents.persistence.tables import metadata

    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{(Path(tmp) / 'feature.db').as_posix()}"
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        config.attributes["configure_logger"] = False
        command.upgrade(config, "head")
        engine = create_engine(url)
        tables = sorted(sa_inspect(engine).get_table_names())
        with engine.connect() as conn:
            context = MigrationContext.configure(conn, opts={"compare_type": True, "target_metadata": metadata})
            diff = compare_metadata(context, metadata)
            revision = context.get_current_revision()
        engine.dispose()
    show("revision", revision)
    show(f"tables ({len(tables)})", ", ".join(tables))
    show("autogenerate diff vs tables.py", diff)
    assert revision == "0001_initial" and diff == [] and len(tables) == 22
except ModuleNotFoundError as exc:  # pragma: no cover - ADR-0025 packages missing
    show("skipped", f"package {exc.name} not installed (ADR-0025)")

# ---------------------------------------------------------------------------------------
section("13. GET /api/health on the skeleton app (ADR-0032)")
from fastapi.testclient import TestClient  # noqa: E402

from launch_agents.api.app import create_app  # noqa: E402

app = create_app(settings=load_settings({"APP_ENV": "test"}))
client = TestClient(app)
health = client.get("/api/health")
show("GET /api/health", f"{health.status_code} {health.json()}")
missing = client.get("/api/nope")
show("GET /api/nope", f"{missing.status_code} {missing.json()}")
show("app.state.services", app.state.services)
assert health.status_code == 200 and health.json() == {"status": "ok"} and missing.status_code == 404

# ---------------------------------------------------------------------------------------
section("14. Typed stubs: exact signatures, owner ticket (behaviour arrives with the owner)")
OWNER = re.compile(r"implemented in (T-\d{3})")
stubs = []
module_names = ["launch_agents"] + [m.name for m in pkgutil.walk_packages(launch_agents.__path__, "launch_agents.")]
for module_name in sorted(module_names):
    module = importlib.import_module(module_name)
    for name, obj in vars(module).items():
        if getattr(obj, "__module__", None) != module_name or name.startswith("_"):
            continue
        targets = []
        if inspect.isfunction(obj):
            targets.append((name, obj))
        elif inspect.isclass(obj):
            targets += [(f"{name}.{m}", f) for m, f in vars(obj).items()
                        if inspect.isfunction(f) and (not m.startswith("_") or m == "__call__")]
        for qualname, func in targets:
            source = inspect.getsource(func)
            match = OWNER.search(source)
            if "raise NotImplementedError" in source and match:
                stubs.append((match.group(1), f"{module_name}:{qualname}{inspect.signature(func)}"))
for owner, line in sorted(stubs):
    print(f"[{owner}] {line}")
print(f"\n{len(stubs)} stubs across {len({o for o, _ in stubs})} owner tickets")
assert len(stubs) > 150 and {"T-002", "T-005", "T-016", "T-024", "T-038"} <= {o for o, _ in stubs}

print("\nFEATURE RUN T-001: OK")
