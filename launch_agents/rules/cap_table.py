"""Share allocation and vesting schedules (ADR-0013). Owned by T-003.

Must not import ``rules.validation``: callers pass facts already normalised by ``validate_facts``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

from ..domain.cap_table import CapTable, VestingEvent
from ..domain.constants import AUTHORIZED_SHARES
from ..domain.types import CaseFacts

__all__ = ["allocate_shares", "build_cap_table", "vesting_schedule"]


def build_cap_table(facts: CaseFacts) -> CapTable:
    """The cap table of normalised facts; ``FactsNotReadyError`` when founders, a 100 % split,
    the entity type, the incorporation date or any vesting term is missing (T-003)."""
    raise NotImplementedError("build_cap_table is implemented in T-003")


def allocate_shares(percents: Sequence[Decimal], total: int = AUTHORIZED_SHARES) -> list[int]:
    """Largest-remainder allocation; ties broken by founder order; sums to ``total`` (T-003)."""
    raise NotImplementedError("allocate_shares is implemented in T-003")


def vesting_schedule(total: int, vesting_months: int, cliff_months: int, start: date) -> list[VestingEvent]:
    """Monthly vesting with a cliff, cumulative-floor so no share is lost (T-003)."""
    raise NotImplementedError("vesting_schedule is implemented in T-003")
