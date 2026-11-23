"""T-047 feature run: the Keelstart brand (ADR-0041) and support wording without reply times (ADR-0042).

Run: bash scripts/py.sh evidence/T-047/feature_run.py   (recorded by scripts/record_run.sh T-047)
Prints the real inputs and outputs and asserts the key results; exits non-zero on failure. No network.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from launch_agents.agents.manager import manager_greeting  # noqa: E402
from launch_agents.config import load_settings  # noqa: E402
from launch_agents.domain import PlanId, SupportLevel  # noqa: E402
from launch_agents.domain.constants import BRAND_NAME  # noqa: E402
from launch_agents.pdf import render_docx, render_signed_pdf  # noqa: E402

REPLY_TIME_PHRASES = ("reply within", "respond within", "response time", "business day", "same day", "answered first")
OLD_BRAND = "Charter" + "ly"
failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(f"  [{'ok' if ok else 'FAIL'}] {what}")
    if not ok:
        failures.append(what)


print("== 1. Brand constant and settings (ADR-0041)")
default = load_settings({})
override = load_settings({"BRAND_NAME": "Acme"})
print(f"  BRAND_NAME                              = {BRAND_NAME!r}")
print(f"  load_settings({{}}).brand_name            = {default.brand_name!r}")
print(f"  load_settings({{'BRAND_NAME': 'Acme'}})   = {override.brand_name!r}")
check(BRAND_NAME == "Keelstart", "BRAND_NAME is 'Keelstart'")
check(default.brand_name == "Keelstart", "default Settings.brand_name is 'Keelstart'")
check(override.brand_name == "Acme", "BRAND_NAME env still overrides the default")

print("\n== 2. Manager greeting")
greeting = manager_greeting(default.brand_name)
print(f"  {greeting.content}")
check("the Manager at Keelstart" in greeting.content, "greeting says 'the Manager at Keelstart'")
check("the Manager at Acme" in manager_greeting(override.brand_name).content, "greeting follows an overridden brand")

print("\n== 3. PDF / Word renderer defaults (inspect.signature)")
for fn in (render_signed_pdf, render_docx):
    param = inspect.signature(fn).parameters["brand_name"]
    print(f"  {fn.__name__}: {param}")
    check(param.default == "Keelstart" and param.default is BRAND_NAME,
          f"{fn.__name__} default brand_name is the BRAND_NAME constant 'Keelstart'")

print("\n== 4. Plans from Settings.plans() (ADR-0042)")
expected = {PlanId.FREE: (SupportLevel.BASIC, "Email support"),
            PlanId.LAUNCH: (SupportLevel.STANDARD, "Email support"),
            PlanId.TEAM: (SupportLevel.PRIORITY, "Priority support")}
plans = default.plans()
for plan_id, plan in plans.items():
    print(f"  {plan.name}: support={plan.support.value} support_label={plan.support_label!r}")
    for h in plan.highlights:
        print(f"      - {h}")
    support, label = expected[plan_id]
    check((plan.support, plan.support_label) == (support, label), f"{plan.name}: {support.value} / {label!r}")
    check(plan.highlights[-1] == label, f"{plan.name}: support label is the last highlight")

print("\n== 5. No-promise check over every label and highlight")
variants = {
    "defaults": plans,
    "yearly disabled": load_settings({"BILLING_YEARLY_ENABLED": "0"}).plans(),
    "overridden amounts": load_settings({"PLAN_TEAM_MAX_COMPANIES": "50", "PLAN_LAUNCH_AI_MESSAGES": "5000",
                                         "PLAN_FREE_MAX_COMPANIES": "2"}).plans(),
}
for name, variant in variants.items():
    texts = [t for p in variant.values() for t in (p.support_label, *p.highlights)]
    hits = sorted({(t, ph) for t in texts for ph in REPLY_TIME_PHRASES if ph in t.lower()})
    print(f"  {name}: {len(texts)} texts checked, reply-time phrases found: {hits or 'none'}")
    check(hits == [], f"{name}: no reply-time promise")

print("\n== 6. Brand scan over launch_agents/")
pkg = ROOT / "launch_agents"
with_new, with_old = [], []
for path in sorted(pkg.rglob("*")):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    rel = path.relative_to(ROOT).as_posix()
    if path.suffix == ".py" and "Keelstart" in text:
        with_new.append(rel)
    if OLD_BRAND.lower() in text.lower():
        with_old.append(rel)
env_old = OLD_BRAND.lower() in (ROOT / ".env.example").read_text(encoding="utf-8").lower()
print(f"  files containing 'Keelstart': {with_new}")
print(f"  files containing the old name: {with_old or 'none'}; in .env.example: {env_old}")
check(with_new == ["launch_agents/domain/constants.py"], "'Keelstart' is spelled only in domain/constants.py")
check(with_old == [] and not env_old, "the old name appears nowhere in launch_agents/ or .env.example")

print()
if failures:
    print(f"FEATURE RUN T-047: FAIL ({len(failures)} check(s) failed)")
    sys.exit(1)
print("FEATURE RUN T-047: PASS")
