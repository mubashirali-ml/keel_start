"""T-003 feature run: cap table, vesting schedules and CSV / Excel exports, used as a caller would.

Run: bash scripts/py.sh evidence/T-003/feature_run.py   (recorded by scripts/record_run.sh T-003)
Prints the real inputs and outputs and asserts the key results; exits non-zero on failure. No network.
"""

from __future__ import annotations

import io
import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402

from launch_agents.domain import CaseFacts, EntityType, Founder  # noqa: E402
from launch_agents.domain.cap_table import CapTable  # noqa: E402
from launch_agents.domain.constants import (  # noqa: E402
    AUTHORIZED_SHARES,
    DEFAULT_CLIFF_MONTHS,
    DEFAULT_VESTING_MONTHS,
)
from launch_agents.domain.errors import FactsNotReadyError  # noqa: E402
from launch_agents.domain.helpers import add_months  # noqa: E402
from launch_agents.rules.cap_table import allocate_shares, build_cap_table, vesting_schedule  # noqa: E402
from launch_agents.rules.exports import cap_table_csv, cap_table_xlsx  # noqa: E402


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def check(cond: bool, what: str) -> None:
    if not cond:
        raise AssertionError(what)
    print(f"  ok  {what}")


def sample_llc() -> CaseFacts:
    """The sample LLC (tests/conftest.py::sample_facts): Bob has no vesting stated."""
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


def apply_defaults_here(facts: CaseFacts) -> CaseFacts:
    """ADR-0013 48/12 defaults, applied in this script (rules.validation belongs to T-002)."""
    out = facts.model_copy(deep=True)
    for f in out.founders:
        if f.vesting_months is None and f.cliff_months is None:
            f.vesting_months, f.cliff_months = DEFAULT_VESTING_MONTHS, DEFAULT_CLIFF_MONTHS
            print(f"  default applied: {f.name} -> {DEFAULT_VESTING_MONTHS} months, {DEFAULT_CLIFF_MONTHS}-month cliff")
    return out


def print_cap(cap: CapTable) -> None:
    label = cap.unit_label.capitalize()
    print(f"  entity={cap.entity_type.value}  unit_label={cap.unit_label}  authorized={cap.authorized:,}  "
          f"vesting_start={cap.vesting_start}  total_issued={cap.total_issued:,}")
    print(f"  {'Founder':<14}{'Email':<22}{'Equity %':>9}{label:>12}{'Vest':>6}{'Cliff':>6}")
    for r in cap.rows:
        print(f"  {r.name:<14}{r.email:<22}{str(r.equity_percent):>9}{r.shares:>12,}{r.vesting_months:>6}"
              f"{r.cliff_months:>6}")


def print_schedule(cap: CapTable) -> None:
    for r in cap.rows:
        print(f"  -- {r.name}: {len(r.schedule)} vesting events (first 14, last 2)")
        shown = r.schedule[:14]
        for ev in shown:
            print(f"     month {ev.month:>2}  {ev.date}  vested {ev.vested_this_event:>10,}  cumulative {ev.cumulative_vested:>10,}")
        if len(r.schedule) > 14:
            print("     ...")
            for ev in r.schedule[-2:]:
                print(f"     month {ev.month:>2}  {ev.date}  vested {ev.vested_this_event:>10,}  cumulative {ev.cumulative_vested:>10,}")


def main() -> int:
    section("1. Sample LLC: facts not ready until vesting defaults are applied")
    raw = sample_llc()
    for f in raw.founders:
        print(f"  input: {f.id} {f.name} {f.equity_percent}% vesting={f.vesting_months} cliff={f.cliff_months}")
    try:
        build_cap_table(raw)
        raise AssertionError("expected FactsNotReadyError for Bob's missing vesting")
    except FactsNotReadyError as exc:
        print(f"  FactsNotReadyError({exc.code}): {exc.message}")
        check("Bob Diaz" in exc.message, "the friendly message names the founder whose vesting is missing")
    facts = apply_defaults_here(raw)

    section("2. Sample LLC cap table")
    cap = build_cap_table(facts)
    print_cap(cap)
    check(cap.unit_label == "units", "an LLC issues units")
    check(cap.total_issued == cap.authorized == AUTHORIZED_SHARES == 10_000_000, "exactly 10,000,000 issued")
    check(sum(r.shares for r in cap.rows) == 10_000_000, "rows sum to 10,000,000")
    check([r.shares for r in cap.rows] == [6_000_000, 4_000_000], "60/40 -> 6,000,000 / 4,000,000")

    section("3. Vesting schedules (48 months, 12-month cliff, from the incorporation date)")
    print_schedule(cap)
    for r in cap.rows:
        first = r.schedule[0]
        check(first.month == 12 and first.vested_this_event == r.shares // 4,
              f"{r.name}: nothing before month 12, cliff vests {r.shares // 4:,} on {first.date}")
        monthly = sorted({ev.vested_this_event for ev in r.schedule[1:]})
        check([ev.month for ev in r.schedule] == list(range(12, 49))
              and set(monthly) <= {r.shares // 48, -(-r.shares // 48)},
              f"{r.name}: months 13-48 each vest {' or '.join(f'{m:,}' for m in monthly)} (cumulative floor)")
        check(sum(ev.vested_this_event for ev in r.schedule) == r.shares, f"{r.name}: events sum to the grant")
        check(r.schedule[-1].month == 48 and r.schedule[-1].cumulative_vested == r.shares,
              f"{r.name}: fully vested ({r.shares:,}) at month 48 on {r.schedule[-1].date}")
        check(all(ev.date == add_months(cap.vesting_start, ev.month) for ev in r.schedule),
              f"{r.name}: dates step by add_months from {cap.vesting_start}")

    section("4. Edge schedules: 4,800,000 over 48/12; 3,333,333 non-divisible; 0/0; cliff == vesting; Jan-31 start")
    s = vesting_schedule(4_800_000, 48, 12, date(2026, 12, 1))
    print(f"  4,800,000 48/12: month {s[0].month} vests {s[0].vested_this_event:,}; month {s[1].month} vests "
          f"{s[1].vested_this_event:,}; last month {s[-1].month} cumulative {s[-1].cumulative_vested:,}")
    check(s[0].month == 12 and s[0].vested_this_event == 1_200_000 and s[1].vested_this_event == 100_000,
          "cliff 1,200,000 then 100,000 a month")
    s = vesting_schedule(3_333_333, 48, 12, date(2026, 12, 1))
    print(f"  3,333,333 48/12: cliff {s[0].vested_this_event:,}; monthly amounts {sorted({e.vested_this_event for e in s[1:]})}; "
          f"sum {sum(e.vested_this_event for e in s):,}")
    check(sum(e.vested_this_event for e in s) == 3_333_333, "no share lost or invented")
    s = vesting_schedule(5_000_000, 0, 0, date(2026, 12, 1))
    print(f"  5,000,000 0/0: {[(e.month, str(e.date), e.vested_this_event) for e in s]}")
    check(len(s) == 1 and s[0].month == 0 and s[0].vested_this_event == 5_000_000, "0/0 vests everything at month 0")
    s = vesting_schedule(2_500_000, 24, 24, date(2026, 12, 1))
    print(f"  2,500,000 24/24: {[(e.month, str(e.date), e.vested_this_event) for e in s]}")
    check(len(s) == 1 and s[0].month == 24, "cliff == vesting vests everything at the cliff")
    s = vesting_schedule(1_200, 12, 0, date(2027, 1, 31))
    print(f"  Jan-31 start dates: {[str(e.date) for e in s[:4]]}")
    check([e.date for e in s[:3]] == [date(2027, 2, 28), date(2027, 3, 31), date(2027, 4, 30)],
          "month-end clamping from Jan 31")

    section("5. Three-way 33.33 / 33.33 / 33.34 Delaware C-Corp")
    corp_facts = CaseFacts(
        business_description="robot espresso carts",
        founders=[
            Founder(id="f1", name="Ana Ruiz", email="ana@example.com", equity_percent=Decimal("33.33"),
                    vesting_months=48, cliff_months=12),
            Founder(id="f2", name="Ben Ode", email="ben@example.com", equity_percent=Decimal("33.33"),
                    vesting_months=48, cliff_months=12),
            Founder(id="f3", name="Cai Lin", email="cai@example.com", equity_percent=Decimal("33.34"),
                    vesting_months=48, cliff_months=12),
        ],
        entity_type=EntityType.C_CORP,
        state="DE",
        incorporation_date=date(2027, 1, 31),
    )
    corp = build_cap_table(corp_facts)
    print_cap(corp)
    check(corp.unit_label == "shares", "a C-Corp issues shares")
    check([r.shares for r in corp.rows] == [3_333_000, 3_333_000, 3_334_000], "3,333,000 / 3,333,000 / 3,334,000")
    check(corp.total_issued == 10_000_000, "exactly 10,000,000 issued")
    print(f"  allocate_shares(['33.33','33.33','33.34'], total=10) -> {allocate_shares([Decimal('33.33'), Decimal('33.33'), Decimal('33.34')], 10)}")

    section("6. CSV and XLSX exports, written to a temp dir and read back")
    with tempfile.TemporaryDirectory() as tmp:
        for name, c in (("llc", cap), ("corp", corp)):
            csv_text = cap_table_csv(c)
            csv_path = Path(tmp) / f"cap_table_{name}.csv"
            csv_path.write_bytes(csv_text.encode("utf-8"))
            xlsx_path = Path(tmp) / f"cap_table_{name}.xlsx"
            xlsx_path.write_bytes(cap_table_xlsx(c))
            print(f"  wrote {csv_path.name} ({csv_path.stat().st_size} bytes) and {xlsx_path.name} "
                  f"({xlsx_path.stat().st_size} bytes)")
            print("  CSV:")
            for line in csv_path.read_bytes().decode("utf-8").split("\n"):
                if line:
                    print(f"    {line}")
            check(b"\r" not in csv_path.read_bytes(), f"{name} CSV uses \\n line endings")
            header = csv_text.split("\n")[0]
            check(header == f"Founder,Email,Equity %,{c.unit_label.capitalize()},Vesting months,Cliff months,Fully vested on",
                  f"{name} CSV header is the ADR-0013 header")
            wb = load_workbook(io.BytesIO(xlsx_path.read_bytes()))
            print(f"  XLSX sheets: {wb.sheetnames}")
            rows = list(wb["Cap table"].iter_rows(values_only=True))
            print(f"  XLSX 'Cap table' total row: {rows[-1]}")
            vest_rows = list(wb["Vesting"].iter_rows(values_only=True))
            print(f"  XLSX 'Vesting': header {vest_rows[0]}, {len(vest_rows) - 1} event rows; first {vest_rows[1]}")
            check(wb.sheetnames == ["Cap table", "Vesting"], f"{name} workbook has 'Cap table' and 'Vesting'")
            check(rows[-1][0] == "Total" and rows[-1][3] == 10_000_000, f"{name} total row = 10,000,000")
            check(len(vest_rows) - 1 == sum(len(r.schedule) for r in c.rows), f"{name} vesting sheet lists every event")

    print()
    print("FEATURE RUN T-003: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FEATURE RUN T-003: FAIL: {exc}")
        sys.exit(1)
