"""Cap table types (ADR-0013). The rules live in ``rules/cap_table.py`` (T-003)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from .constants import AUTHORIZED_SHARES
from .types import EntityType

__all__ = ["CapTable", "CapTableRow", "VestingEvent"]


class VestingEvent(BaseModel):
    month: int  # 0 = start (only when vesting_months == 0), else 1..vesting_months
    date: date  # add_months(start, month)
    vested_this_event: int
    cumulative_vested: int


class CapTableRow(BaseModel):
    founder_id: str
    name: str
    email: str
    equity_percent: Decimal
    shares: int
    vesting_months: int
    cliff_months: int
    schedule: list[VestingEvent]  # only events where vested_this_event > 0


class CapTable(BaseModel):
    entity_type: EntityType
    unit_label: Literal["shares", "units"]  # "units" for LLC
    authorized: int = AUTHORIZED_SHARES
    vesting_start: date  # = incorporation_date
    rows: list[CapTableRow]  # founder order
    total_issued: int  # always == authorized
