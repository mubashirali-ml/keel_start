"""T-003: share allocation, vesting schedule and build_cap_table (ADR-0013)."""

from __future__ import annotations

import ast
import random
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from launch_agents.domain import CaseFacts, EntityType, Founder
from launch_agents.domain.cap_table import CapTable, VestingEvent
from launch_agents.domain.constants import AUTHORIZED_SHARES
from launch_agents.domain.errors import FactsNotReadyError
from launch_agents.domain.helpers import add_months
from launch_agents.rules.cap_table import allocate_shares, build_cap_table, vesting_schedule

D = Decimal


def _pcts(*values: str) -> list[Decimal]:
    return [D(v) for v in values]


def _founder(i: int, pct: str, vesting: int | None = 48, cliff: int | None = 12) -> Founder:
    return Founder(id=f"f{i}", name=f"Founder {i}", email=f"f{i}@example.com", equity_percent=D(pct),
                   vesting_months=vesting, cliff_months=cliff)


def _facts(founders: list[Founder], entity: EntityType | None = EntityType.LLC,
           inc: date | None = date(2026, 12, 1)) -> CaseFacts:
    return CaseFacts(business_description="x", founders=founders, entity_type=entity, state="DE",
                     incorporation_date=inc)


# --------------------------------------------------------------------------------------
# AC1: allocate_shares sums to exactly total
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "percents, expected",
    [
        (("60", "40"), [6_000_000, 4_000_000]),
        (("50", "50"), [5_000_000, 5_000_000]),
        (("33.33", "33.33", "33.34"), [3_333_000, 3_333_000, 3_334_000]),
        (("1", "99"), [100_000, 9_900_000]),
        (("10",) * 10, [1_000_000] * 10),
    ],
)
def test_allocate_shares_named_splits(percents, expected):
    shares = allocate_shares(_pcts(*percents))
    assert shares == expected
    assert sum(shares) == AUTHORIZED_SHARES


def test_allocate_shares_default_total_is_authorized_shares():
    assert sum(allocate_shares(_pcts("100"))) == AUTHORIZED_SHARES == 10_000_000


def test_allocate_shares_property_200_random_two_decimal_splits():
    rng = random.Random(20261123)
    for _ in range(200):
        n = rng.randint(1, 12)
        # n positive integer amounts of hundredths of a percent that sum to 10000 (= 100.00 %)
        cuts = sorted(rng.sample(range(1, 10_000), n - 1))
        parts = [b - a for a, b in zip([0, *cuts], [*cuts, 10_000])]
        percents = [D(p) / 100 for p in parts]
        assert sum(percents) == 100
        for total in (AUTHORIZED_SHARES, 7, 9_999_999):
            shares = allocate_shares(percents, total)
            assert sum(shares) == total
            assert len(shares) == n
            for p, s in zip(percents, shares):
                exact = D(total) * p / 100
                assert abs(D(s) - exact) < 1  # never more than one share off the exact amount


def test_allocate_shares_ties_broken_by_founder_order():
    # 10 shares at 33.33/33.33/33.34: the one leftover share goes to the largest fraction (0.334).
    assert allocate_shares(_pcts("33.33", "33.33", "33.34"), 10) == [3, 3, 4]
    # 100 shares at 33.335/33.335/33.33: leftover 1 share, the two equal 0.335 fractions tie -> first.
    assert allocate_shares(_pcts("33.335", "33.335", "33.33"), 100) == [34, 33, 33]
    # Exactly equal fractional parts: 50/50 of 3 shares -> 1.5 each, the first founder wins.
    assert allocate_shares(_pcts("50", "50"), 3) == [2, 1]
    # Four equal founders of 2 shares -> 0.5 each: the first two get the leftovers.
    assert allocate_shares(_pcts("25", "25", "25", "25"), 2) == [1, 1, 0, 0]


def test_allocate_shares_largest_remainder_wins_over_order():
    # 1 share: 30 % -> 0.3, 70 % -> 0.7; the larger fraction gets it even though it is later.
    assert allocate_shares(_pcts("30", "70"), 1) == [0, 1]


@pytest.mark.parametrize("percents", [[], _pcts("60", "30"), _pcts("60", "50"), _pcts("110", "-10")])
def test_allocate_shares_rejects_bad_input(percents):
    with pytest.raises(ValueError):
        allocate_shares(percents)


def test_allocate_shares_rejects_negative_total():
    with pytest.raises(ValueError):
        allocate_shares(_pcts("100"), -1)


# --------------------------------------------------------------------------------------
# AC2: unit label and totals
# --------------------------------------------------------------------------------------
def test_llc_uses_units_and_issues_exactly_authorized(sample_facts):
    sample_facts.founders[1].vesting_months = 48
    sample_facts.founders[1].cliff_months = 12
    cap = build_cap_table(sample_facts)
    assert isinstance(cap, CapTable)
    assert cap.unit_label == "units"
    assert cap.entity_type == EntityType.LLC
    assert cap.total_issued == cap.authorized == 10_000_000
    assert [r.shares for r in cap.rows] == [6_000_000, 4_000_000]
    assert [r.founder_id for r in cap.rows] == ["f1", "f2"]
    assert cap.vesting_start == date(2026, 12, 1)


def test_c_corp_uses_shares():
    cap = build_cap_table(_facts([_founder(1, "33.33"), _founder(2, "33.33"), _founder(3, "33.34")],
                                 entity=EntityType.C_CORP))
    assert cap.unit_label == "shares"
    assert cap.total_issued == cap.authorized == 10_000_000
    assert sum(r.shares for r in cap.rows) == 10_000_000
    assert [r.shares for r in cap.rows] == [3_333_000, 3_333_000, 3_334_000]


def test_rows_copy_founder_fields_and_carry_schedules():
    cap = build_cap_table(_facts([_founder(1, "70", 36, 6), _founder(2, "30", 0, 0)]))
    r1, r2 = cap.rows
    assert (r1.name, r1.email, r1.equity_percent, r1.vesting_months, r1.cliff_months) == \
        ("Founder 1", "f1@example.com", D("70"), 36, 6)
    assert r1.schedule == vesting_schedule(r1.shares, 36, 6, cap.vesting_start)
    assert r1.schedule[-1].cumulative_vested == r1.shares
    assert r2.schedule == [VestingEvent(month=0, date=date(2026, 12, 1), vested_this_event=3_000_000,
                                        cumulative_vested=3_000_000)]


# --------------------------------------------------------------------------------------
# AC3: standard 48/12 schedule
# --------------------------------------------------------------------------------------
def test_vesting_48_12_for_4_8_million():
    start = date(2026, 12, 1)
    events = vesting_schedule(4_800_000, 48, 12, start)
    by_month = {e.month: e for e in events}
    # months 1-11 vest nothing (and are not listed: only events with vested > 0)
    assert all(m not in by_month for m in range(1, 12))
    assert by_month[12].vested_this_event == 1_200_000
    assert by_month[12].cumulative_vested == 1_200_000
    for m in range(13, 49):
        assert by_month[m].vested_this_event == 100_000
        assert by_month[m].cumulative_vested == 1_200_000 + 100_000 * (m - 12)
    assert [e.month for e in events] == list(range(12, 49))
    assert events[-1].month == 48
    assert events[-1].cumulative_vested == 4_800_000
    assert sum(e.vested_this_event for e in events) == 4_800_000
    for e in events:
        assert e.date == add_months(start, e.month)
    assert by_month[12].date == date(2027, 12, 1)
    assert by_month[48].date == date(2030, 12, 1)


def test_vesting_dates_clamp_to_month_end_from_jan_31():
    start = date(2027, 1, 31)
    events = vesting_schedule(1_200, 12, 0, start)
    dates = {e.month: e.date for e in events}
    assert dates[1] == date(2027, 2, 28)
    assert dates[2] == date(2027, 3, 31)
    assert dates[3] == date(2027, 4, 30)
    assert dates[12] == date(2028, 1, 31)
    # A leap year: Jan 31 2028 + 1 month = Feb 29 2028.
    leap = vesting_schedule(100, 1, 0, date(2028, 1, 31))
    assert leap[0].date == date(2028, 2, 29)
    # Dates are always computed from the start, never chained (no drift to the 28th).
    for e in events:
        assert e.date == add_months(start, e.month)


def test_cliff_zero_vests_monthly_from_month_one():
    events = vesting_schedule(1_200, 12, 0, date(2026, 12, 1))
    assert [e.month for e in events] == list(range(1, 13))
    assert all(e.vested_this_event == 100 for e in events)


# --------------------------------------------------------------------------------------
# AC4: non-divisible totals and edge terms
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("total", [3_333_333, 1, 47, 3_333_334, 9_999_999, 6_666_667])
@pytest.mark.parametrize("vesting, cliff", [(48, 12), (36, 6), (12, 0), (7, 3), (48, 48), (1, 1)])
def test_non_divisible_totals_never_lose_or_invent_a_share(total, vesting, cliff):
    events = vesting_schedule(total, vesting, cliff, date(2026, 12, 1))
    assert sum(e.vested_this_event for e in events) == total
    assert events[-1].cumulative_vested == total
    assert events[-1].month == vesting
    running = 0
    for e in events:
        assert e.vested_this_event > 0
        assert cliff <= e.month <= vesting
        running += e.vested_this_event
        assert e.cumulative_vested == running
        assert e.cumulative_vested == (total if e.month == vesting else total * e.month // vesting)


def test_3_333_333_over_48_12_cliff_amount_is_accrued_portion():
    events = vesting_schedule(3_333_333, 48, 12, date(2026, 12, 1))
    assert events[0].month == 12
    assert events[0].vested_this_event == 3_333_333 * 12 // 48 == 833_333
    assert sum(e.vested_this_event for e in events) == 3_333_333
    monthly = {e.vested_this_event for e in events[1:]}
    assert monthly <= {69_444, 69_445}


def test_zero_vesting_vests_everything_at_month_zero():
    start = date(2026, 12, 1)
    events = vesting_schedule(5_000_000, 0, 0, start)
    assert events == [VestingEvent(month=0, date=start, vested_this_event=5_000_000, cumulative_vested=5_000_000)]


def test_cliff_equal_to_vesting_vests_everything_at_the_cliff():
    start = date(2026, 12, 1)
    events = vesting_schedule(3_333_333, 24, 24, start)
    assert events == [VestingEvent(month=24, date=date(2028, 12, 1), vested_this_event=3_333_333,
                                   cumulative_vested=3_333_333)]


def test_zero_total_has_no_events():
    assert vesting_schedule(0, 48, 12, date(2026, 12, 1)) == []
    assert vesting_schedule(0, 0, 0, date(2026, 12, 1)) == []


@pytest.mark.parametrize("total, vesting, cliff", [(-1, 48, 12), (100, -1, 0), (100, 12, -1), (100, 12, 13)])
def test_vesting_schedule_rejects_bad_terms(total, vesting, cliff):
    with pytest.raises(ValueError):
        vesting_schedule(total, vesting, cliff, date(2026, 12, 1))


# --------------------------------------------------------------------------------------
# AC5: build_cap_table raises FactsNotReadyError with a friendly message
# --------------------------------------------------------------------------------------
def test_not_ready_no_founders():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([]))
    assert exc.value.code == "facts_not_ready"
    assert "at least one founder" in exc.value.message


def test_not_ready_equity_not_100():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "60"), _founder(2, "30")]))
    assert exc.value.message.startswith("Equity adds up to 90%; it must total exactly 100%")
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "60.01"), _founder(2, "40")]))
    assert "100.01%" in exc.value.message


def test_not_ready_bad_single_equity():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "110"), _founder(2, "-10")]))
    assert "Founder 1" in exc.value.message


def test_not_ready_missing_entity_type():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "100")], entity=None))
    assert "LLC or a Delaware C-Corp" in exc.value.message


def test_not_ready_missing_incorporation_date():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "100")], inc=None))
    assert "incorporation date" in exc.value.message


@pytest.mark.parametrize("vesting, cliff", [(None, None), (48, None), (None, 12)])
def test_not_ready_any_vesting_value_none(vesting, cliff, sample_facts):
    sample_facts.founders[1].vesting_months = vesting
    sample_facts.founders[1].cliff_months = cliff
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(sample_facts)
    assert "Bob Diaz" in exc.value.message
    assert "vesting" in exc.value.message
    assert exc.value.details["founder_id"] == "f2"


def test_sample_facts_without_defaults_are_not_ready(sample_facts):
    # Bob has no vesting stated: callers must apply validate_facts' defaults first.
    with pytest.raises(FactsNotReadyError):
        build_cap_table(sample_facts)


def test_not_ready_cliff_longer_than_vesting():
    with pytest.raises(FactsNotReadyError) as exc:
        build_cap_table(_facts([_founder(1, "100", 12, 24)]))
    assert "cliff" in exc.value.message


def test_messages_are_friendly_sentences():
    cases = [_facts([]), _facts([_founder(1, "50")]), _facts([_founder(1, "100")], entity=None),
             _facts([_founder(1, "100")], inc=None), _facts([_founder(1, "100", None, None)])]
    for facts in cases:
        with pytest.raises(FactsNotReadyError) as exc:
            build_cap_table(facts)
        msg = exc.value.message
        assert msg[0].isupper() and msg.endswith(".")
        assert "None" not in msg and "Traceback" not in msg


# --------------------------------------------------------------------------------------
# Contract: rules.cap_table does not import rules.validation (built in parallel by T-002)
# --------------------------------------------------------------------------------------
def test_cap_table_module_does_not_import_validation():
    import launch_agents.rules.cap_table as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(("." * node.level) + (node.module or ""))
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
    assert not any("validation" in name for name in imported), imported
