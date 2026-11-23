"""T-003: CSV and Excel export of the cap table (ADR-0013)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from launch_agents.domain import CaseFacts, EntityType, Founder
from launch_agents.rules.cap_table import build_cap_table
from launch_agents.rules.exports import cap_table_csv, cap_table_xlsx

D = Decimal
HEADER_TAIL = "Vesting months,Cliff months,Fully vested on"


@pytest.fixture
def llc_cap(sample_facts):
    sample_facts.founders[1].vesting_months = 48  # defaults applied as validate_facts would
    sample_facts.founders[1].cliff_months = 12
    return build_cap_table(sample_facts)


@pytest.fixture
def corp_cap():
    founders = [
        Founder(id="f1", name="Ana, Jr.", email="ana@example.com", equity_percent=D("33.33"),
                vesting_months=48, cliff_months=12),
        Founder(id="f2", name="Bea \"B\" Lu", email="bea@example.com", equity_percent=D("33.33"),
                vesting_months=36, cliff_months=0),
        Founder(id="f3", name="Cai Zoë", email="cai@example.com", equity_percent=D("33.34"),
                vesting_months=0, cliff_months=0),
    ]
    facts = CaseFacts(business_description="x", founders=founders, entity_type=EntityType.C_CORP, state="DE",
                      incorporation_date=date(2027, 1, 31))
    return build_cap_table(facts)


# --------------------------------------------------------------------------------------
# AC6: CSV
# --------------------------------------------------------------------------------------
def test_csv_llc_exact_header_rows_and_newlines(llc_cap):
    text = cap_table_csv(llc_cap)
    assert "\r" not in text
    assert text.endswith("\n")
    lines = text.split("\n")[:-1]
    assert lines[0] == f"Founder,Email,Equity %,Units,{HEADER_TAIL}"
    assert lines[1:] == [
        "Alice Chen,alice@example.com,60,6000000,48,12,2030-12-01",
        "Bob Diaz,bob@example.com,40,4000000,48,12,2030-12-01",
    ]


def test_csv_c_corp_uses_shares_header_and_quotes_safely(corp_cap):
    text = cap_table_csv(corp_cap)
    assert text.split("\n")[0] == f"Founder,Email,Equity %,Shares,{HEADER_TAIL}"
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == 1 + 3  # one row per founder
    assert [r[0] for r in rows[1:]] == ["Ana, Jr.", "Bea \"B\" Lu", "Cai Zoë"]
    assert [r[2] for r in rows[1:]] == ["33.33", "33.33", "33.34"]
    assert [r[3] for r in rows[1:]] == ["3333000", "3333000", "3334000"]
    assert sum(int(r[3]) for r in rows[1:]) == 10_000_000
    # Fully vested on: start + vesting months, clamped at month end (Jan 31 start)
    assert [r[6] for r in rows[1:]] == ["2031-01-31", "2030-01-31", "2027-01-31"]


def test_csv_share_counts_are_plain_integers(corp_cap, llc_cap):
    for cap in (corp_cap, llc_cap):
        for r in list(csv.reader(io.StringIO(cap_table_csv(cap))))[1:]:
            for value in (r[3], r[4], r[5]):
                assert value.isdigit(), value  # no separators, no decimals, no sign


def test_csv_is_utf8_encodable(corp_cap):
    assert "Zoë" in cap_table_csv(corp_cap).encode("utf-8").decode("utf-8")


# --------------------------------------------------------------------------------------
# AC6: Excel
# --------------------------------------------------------------------------------------
def _sheet_rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def test_xlsx_opens_with_openpyxl_and_has_both_sheets(llc_cap):
    data = cap_table_xlsx(llc_cap)
    assert isinstance(data, bytes) and data[:2] == b"PK"
    wb = load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Cap table", "Vesting"]


def test_xlsx_cap_table_sheet_columns_rows_and_total(llc_cap):
    wb = load_workbook(io.BytesIO(cap_table_xlsx(llc_cap)))
    rows = _sheet_rows(wb["Cap table"])
    assert rows[0] == ["Founder", "Email", "Equity %", "Units", "Vesting months", "Cliff months", "Fully vested on"]
    assert rows[1][:6] == ["Alice Chen", "alice@example.com", 60, 6_000_000, 48, 12]
    assert rows[2][:6] == ["Bob Diaz", "bob@example.com", 40, 4_000_000, 48, 12]
    assert rows[1][6] == datetime(2030, 12, 1)
    total = rows[-1]
    assert len(rows) == 1 + 2 + 1
    assert total[0] == "Total"
    assert total[2] == 100
    assert total[3] == 10_000_000
    assert isinstance(total[3], int)


def test_xlsx_c_corp_total_and_header(corp_cap):
    wb = load_workbook(io.BytesIO(cap_table_xlsx(corp_cap)))
    rows = _sheet_rows(wb["Cap table"])
    assert rows[0][3] == "Shares"
    assert [r[3] for r in rows[1:4]] == [3_333_000, 3_333_000, 3_334_000]
    assert rows[-1][0] == "Total" and rows[-1][3] == 10_000_000
    assert rows[-1][2] == pytest.approx(100)


def test_xlsx_vesting_sheet_matches_schedules(corp_cap):
    wb = load_workbook(io.BytesIO(cap_table_xlsx(corp_cap)))
    rows = _sheet_rows(wb["Vesting"])
    assert rows[0] == ["Founder", "Month", "Date", "Vested", "Cumulative vested"]
    expected = [
        [row.name, ev.month, datetime.combine(ev.date, datetime.min.time()), ev.vested_this_event,
         ev.cumulative_vested]
        for row in corp_cap.rows for ev in row.schedule
    ]
    assert rows[1:] == expected
    for row in corp_cap.rows:
        assert sum(r[3] for r in rows[1:] if r[0] == row.name) == row.shares
    # Month-0 vesting for the fully vested founder; Feb-28 clamping from the Jan-31 start.
    assert ["Cai Zoë", 0, datetime(2027, 1, 31), 3_334_000, 3_334_000] in rows
    assert ["Bea \"B\" Lu", 1, datetime(2027, 2, 28), 92_583, 92_583] in rows


def test_xlsx_is_deterministic(llc_cap):
    a = load_workbook(io.BytesIO(cap_table_xlsx(llc_cap)))
    b = load_workbook(io.BytesIO(cap_table_xlsx(llc_cap)))
    for name in a.sheetnames:
        assert _sheet_rows(a[name]) == _sheet_rows(b[name])


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_xlsx_formula_like_text_is_stored_literally(prefix):
    name = f"{prefix}1+2"
    email = f"{prefix}HYPERLINK(\"http://x\")@example.com"
    founders = [
        Founder(id="f1", name=name, email=email, equity_percent=D("60"), vesting_months=12, cliff_months=0),
        Founder(id="f2", name="Plain Name", email="plain@example.com", equity_percent=D("40"),
                vesting_months=0, cliff_months=0),
    ]
    facts = CaseFacts(business_description="x", founders=founders, entity_type=EntityType.C_CORP, state="DE",
                      incorporation_date=date(2027, 1, 1))
    wb = load_workbook(io.BytesIO(cap_table_xlsx(build_cap_table(facts))))

    cap_ws = wb["Cap table"]
    assert cap_ws["A2"].value == name and cap_ws["A2"].data_type == "s"
    assert cap_ws["B2"].value == email and cap_ws["B2"].data_type == "s"
    assert cap_ws.cell(row=cap_ws.max_row, column=1).value == "Total"
    vest_ws = wb["Vesting"]
    founder_cells = [r[0] for r in vest_ws.iter_rows(min_row=2) if r[0].value == name]
    assert len(founder_cells) == 12
    # Every text cell in both sheets (headers, names, emails, "Total") is a literal string.
    for ws in (cap_ws, vest_ws):
        for cells in ws.iter_rows():
            for cell in cells:
                if isinstance(cell.value, str):
                    assert cell.data_type == "s", (ws.title, cell.coordinate, cell.value)
                assert cell.data_type != "f", (ws.title, cell.coordinate)
