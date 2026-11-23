"""CSV and Excel export of the cap table (ADR-0013). Owned by T-003."""

from __future__ import annotations

from ..domain.cap_table import CapTable

__all__ = ["cap_table_csv", "cap_table_xlsx"]


def cap_table_csv(cap: CapTable) -> str:
    """Header ``Founder,Email,Equity %,Shares|Units,Vesting months,Cliff months,Fully vested on``;
    ``\n`` line endings, plain integers (T-003)."""
    raise NotImplementedError("cap_table_csv is implemented in T-003")


def cap_table_xlsx(cap: CapTable) -> bytes:
    """Workbook with sheets "Cap table" (+ total row) and "Vesting" (T-003)."""
    raise NotImplementedError("cap_table_xlsx is implemented in T-003")
