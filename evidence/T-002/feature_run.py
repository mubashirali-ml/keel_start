"""T-002 feature run: case validation used the way the Manager, services and UI will use it.

Run: bash scripts/py.sh evidence/T-002/feature_run.py   (recorded by scripts/record_run.sh T-002)
Validates five scenarios end to end, prints the inputs and the real outputs, asserts the
outcome of each and exits non-zero on failure. No network.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from launch_agents.domain import CaseFacts, EntityType, Founder, deadline_83b, days_until  # noqa: E402
from launch_agents.rules import validate_facts  # noqa: E402
from launch_agents.rules.validation import missing_facts  # noqa: E402

TODAY = date(2026, 11, 23)
FAILURES: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}")
    if not condition:
        FAILURES.append(label)


def show_facts(facts: CaseFacts) -> None:
    print("  input:")
    print(f"    business_description: {facts.business_description!r}")
    print(f"    entity_type:          {facts.entity_type.value if facts.entity_type else None}")
    print(f"    state:                {facts.state!r}")
    print(f"    incorporation_date:   {facts.incorporation_date}")
    for f in facts.founders:
        print(f"    founder {f.id}: {f.name!r} <{f.email}> {f.equity_percent}% "
              f"vesting={f.vesting_months} cliff={f.cliff_months}")


def show_result(result) -> None:
    print("  output:")
    print(f"    ok:      {result.ok}")
    print(f"    missing: {result.missing}")
    print(f"    notes:   {result.notes}")
    print(f"    issues:  {len(result.issues)}")
    for i in result.issues:
        print(f"      - {i.code} (field={i.field}, founder={i.founder_id}): {i.message}")
    for f in result.facts.founders:
        print(f"    normalised {f.id}: vesting={f.vesting_months} cliff={f.cliff_months}")


def scenario(title: str, facts: CaseFacts):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)
    show_facts(facts)
    before = facts.model_dump()
    result = validate_facts(facts)
    show_result(result)
    check(facts.model_dump() == before, "input facts were not mutated")
    return result


def sample() -> CaseFacts:
    """The shared sample case (tests/conftest.py ``sample_facts``)."""
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


def main() -> int:
    # 1. The sample two-founder LLC
    facts = sample()
    r = scenario("1. Sample two-founder Wyoming LLC (Bob has no vesting stated)", facts)
    check(r.ok is True, "ok is True")
    check(r.issues == [] and r.missing == [], "no issues, nothing missing")
    check(r.notes == ["No vesting was given for Bob Diaz, so I used the standard 48 months "
                      "with a 12-month cliff."], "one default-vesting note naming Bob")
    bob = r.facts.founders[1]
    check((bob.vesting_months, bob.cliff_months) == (48, 12), "Bob normalised to 48/12")
    check(facts.founders[1].vesting_months is None, "caller's Bob still has no vesting (pure)")

    deadline = deadline_83b(r.facts.incorporation_date)
    left = days_until(deadline, TODAY)
    print(f"  83(b) deadline: {deadline.isoformat()} ({left} days from {TODAY.isoformat()})")
    check(deadline == date(2026, 12, 31), "83(b) deadline is incorporation date + 30 days = 2026-12-31")
    check(left == 38, "38 days left on 2026-11-23")

    # 2. Equity sums to 90%
    facts = sample()
    facts.founders[1].equity_percent = Decimal("30")
    r = scenario("2. Equity adds up to 90% (60 + 30)", facts)
    check(r.ok is False, "ok is False")
    check([i.code for i in r.issues] == ["equity_total"], "exactly one issue: equity_total")
    check("90%" in r.issues[0].message, "message states the 90% total")

    # 3. Cliff longer than vesting
    facts = sample()
    facts.founders[1].vesting_months, facts.founders[1].cliff_months = 12, 13
    r = scenario("3. Bob's cliff (13 months) is longer than his vesting (12 months)", facts)
    check(r.ok is False, "ok is False")
    check([(i.code, i.founder_id) for i in r.issues] == [("cliff_exceeds_vesting", "f2")],
          "exactly one issue: cliff_exceeds_vesting for f2")
    check("Bob Diaz" in r.issues[0].message, "message names Bob Diaz")

    # 4. C-Corp in Wyoming
    facts = sample()
    facts.entity_type = EntityType.C_CORP
    r = scenario("4. Delaware C-Corp with state WY", facts)
    check(r.ok is False, "ok is False")
    check([i.code for i in r.issues] == ["entity_state_mismatch"], "exactly one issue: entity_state_mismatch")

    # 5. Half-filled case
    facts = CaseFacts(
        state="wy",
        founders=[Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("100"))],
    )
    r = scenario("5. Half-filled case (only a state and one founder so far)", facts)
    print("  missing facts in ask order:")
    for n, key in enumerate(r.missing, 1):
        print(f"    {n}. {key}")
    check(r.missing == ["business_description", "entity_type", "incorporation_date"],
          "missing = business_description, entity_type, incorporation_date (ADR order)")
    check(missing_facts(facts) == r.missing, "missing_facts() agrees with validate_facts().missing")
    check(r.issues == [], "no issues: the given facts are valid")
    check(r.ok is False, "ok is False while facts are missing")
    check(r.facts.state == "WY", "state normalised to WY")

    print()
    if FAILURES:
        print(f"FEATURE RUN FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("FEATURE RUN PASSED: all five scenarios behave as ADR-0013 specifies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
