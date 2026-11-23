"""CSV and Excel export of the cap table (ADR-0013). Owned by T-003.

Exports only format a ``CapTable`` built by ``rules.cap_table.build_cap_table``; they never
compute share counts themselves.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font

from ..domain.cap_table import CapTable, CapTableRow
from ..domain.helpers import add_months

__all__ = ["cap_table_csv", "cap_table_xlsx"]

CAP_TABLE_SHEET = "Cap table"
VESTING_SHEET = "Vesting"
VESTING_HEADER = ("Founder", "Month", "Date", "Vested", "Cumulative vested")
_DATE_FORMAT = "yyyy-mm-dd"


def _header(cap: CapTable) -> list[str]:
    return ["Founder", "Email", "Equity %", cap.unit_label.capitalize(), "Vesting months", "Cliff months",
            "Fully vested on"]


def _fully_vested_on(cap: CapTable, row: CapTableRow) -> date:
    """The date of the last vesting event: ``add_months(vesting_start, vesting_months)``."""
    return add_months(cap.vesting_start, row.vesting_months)


def _percent(value: Decimal) -> str:
    """At most two decimals, no trailing zeros, no exponent: ``60`` / ``33.33`` / ``12.5``."""
    text = f"{value.quantize(Decimal('0.01')):f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _literal_text(ws) -> None:
    """Mark every string cell as a literal string.

    openpyxl treats any string starting with ``=`` as a formula. Founder names and emails are
    free text, so a name like ``=1+2`` would otherwise become a computed formula cell
    (spreadsheet formula injection) instead of the founder's real name.
    """
    for cells in ws.iter_rows():
        for cell in cells:
            if isinstance(cell.value, str):
                cell.data_type = "s"


def cap_table_csv(cap: CapTable) -> str:
    """Header ``Founder,Email,Equity %,Shares|Units,Vesting months,Cliff months,Fully vested on``;
    ``\n`` line endings, plain integers (T-003)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_header(cap))
    for row in cap.rows:
        writer.writerow([
            row.name,
            row.email,
            _percent(row.equity_percent),
            str(int(row.shares)),
            str(int(row.vesting_months)),
            str(int(row.cliff_months)),
            _fully_vested_on(cap, row).isoformat(),
        ])
    return buf.getvalue()


def cap_table_xlsx(cap: CapTable) -> bytes:
    """Workbook with sheets "Cap table" (+ total row) and "Vesting" (T-003)."""
    wb = Workbook()
    # Fixed document timestamps so the same cap table always yields the same workbook content.
    stamp = datetime.combine(cap.vesting_start, datetime.min.time())
    wb.properties.created = stamp
    wb.properties.modified = stamp
    bold = Font(bold=True)

    ws = wb.active
    ws.title = CAP_TABLE_SHEET
    ws.append(_header(cap))
    for row in cap.rows:
        ws.append([
            row.name,
            row.email,
            float(_percent(row.equity_percent)),
            int(row.shares),
            int(row.vesting_months),
            int(row.cliff_months),
            _fully_vested_on(cap, row),
        ])
        ws.cell(row=ws.max_row, column=7).number_format = _DATE_FORMAT
    total_percent = sum((r.equity_percent for r in cap.rows), Decimal(0))
    ws.append(["Total", None, float(_percent(total_percent)), int(sum(r.shares for r in cap.rows)), None, None, None])
    for cell in ws[1] + ws[ws.max_row]:
        cell.font = bold
    for col, width in zip("ABCDEFG", (24, 30, 10, 14, 15, 13, 16)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    _literal_text(ws)

    vs = wb.create_sheet(VESTING_SHEET)
    vs.append(list(VESTING_HEADER))
    for cell in vs[1]:
        cell.font = bold
    for row in cap.rows:
        for ev in row.schedule:
            vs.append([row.name, int(ev.month), ev.date, int(ev.vested_this_event), int(ev.cumulative_vested)])
            vs.cell(row=vs.max_row, column=3).number_format = _DATE_FORMAT
    for col, width in zip("ABCDE", (24, 8, 12, 14, 18)):
        vs.column_dimensions[col].width = width
    vs.freeze_panes = "A2"
    _literal_text(vs)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
