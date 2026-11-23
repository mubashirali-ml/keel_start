"""Share allocation and vesting schedules (ADR-0013). Owned by T-003.

Must not import ``rules.validation``: callers pass facts already normalised by ``validate_facts``.

- ``allocate_shares``: largest remainder over exact fractions; leftover shares go one each to
  the largest fractional parts, ties broken by founder order. Always sums to ``total``.
- ``vesting_schedule``: monthly with a cliff, cumulative-floor so no share is lost or invented.
- ``build_cap_table``: the one place share counts are computed; documents and the UI quote it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Sequence

from ..domain.cap_table import CapTable, CapTableRow, VestingEvent
from ..domain.constants import AUTHORIZED_SHARES
from ..domain.errors import FactsNotReadyError
from ..domain.helpers import add_months
from ..domain.types import CaseFacts, EntityType

__all__ = ["allocate_shares", "build_cap_table", "vesting_schedule"]

_HUNDRED = Fraction(100)


def _percent_text(value: Decimal) -> str:
    """``Decimal("90.00")`` -> ``"90"``, ``Decimal("33.3")`` -> ``"33.3"`` (no exponent)."""
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def build_cap_table(facts: CaseFacts) -> CapTable:
    """The cap table of normalised facts; ``FactsNotReadyError`` when founders, a 100 % split,
    the entity type, the incorporation date or any vesting term is missing (T-003)."""
    founders = list(facts.founders)
    if not founders:
        raise FactsNotReadyError(
            "I need at least one founder before I can build the cap table.",
            details={"field": "founders"},
        )
    for f in founders:
        if f.equity_percent <= 0 or f.equity_percent > 100:
            raise FactsNotReadyError(
                f"{f.name}'s equity is {_percent_text(f.equity_percent)}%; each founder needs more than 0% "
                "and at most 100% before I can build the cap table.",
                details={"field": "founders", "founder_id": f.id},
            )
    total_percent = sum((f.equity_percent for f in founders), Decimal(0))
    if total_percent != Decimal(100):
        raise FactsNotReadyError(
            f"Equity adds up to {_percent_text(total_percent)}%; it must total exactly 100% "
            "before I can build the cap table.",
            details={"field": "founders", "equity_total": _percent_text(total_percent)},
        )
    if facts.entity_type is None:
        raise FactsNotReadyError(
            "I need to know whether this is an LLC or a Delaware C-Corp before I can build the cap table.",
            details={"field": "entity_type"},
        )
    if facts.incorporation_date is None:
        raise FactsNotReadyError(
            "I need the incorporation date before I can build the cap table; vesting starts on that date.",
            details={"field": "incorporation_date"},
        )
    for f in founders:
        if f.vesting_months is None or f.cliff_months is None:
            raise FactsNotReadyError(
                f"I still need {f.name}'s vesting terms (vesting months and cliff months) "
                "before I can build the cap table.",
                details={"field": "founders", "founder_id": f.id},
            )
        if f.vesting_months < 0 or f.cliff_months < 0 or f.cliff_months > f.vesting_months:
            raise FactsNotReadyError(
                f"{f.name}'s vesting of {f.vesting_months} months with a {f.cliff_months}-month cliff "
                "doesn't work: the cliff can't be longer than the vesting period, and neither can be negative.",
                details={"field": "founders", "founder_id": f.id},
            )

    unit_label = "units" if facts.entity_type == EntityType.LLC else "shares"
    start = facts.incorporation_date
    shares = allocate_shares([f.equity_percent for f in founders], AUTHORIZED_SHARES)
    rows = [
        CapTableRow(
            founder_id=f.id,
            name=f.name,
            email=f.email,
            equity_percent=f.equity_percent,
            shares=n,
            vesting_months=f.vesting_months,
            cliff_months=f.cliff_months,
            schedule=vesting_schedule(n, f.vesting_months, f.cliff_months, start),
        )
        for f, n in zip(founders, shares)
    ]
    return CapTable(
        entity_type=facts.entity_type,
        unit_label=unit_label,
        authorized=AUTHORIZED_SHARES,
        vesting_start=start,
        rows=rows,
        total_issued=sum(r.shares for r in rows),
    )


def allocate_shares(percents: Sequence[Decimal], total: int = AUTHORIZED_SHARES) -> list[int]:
    """Largest-remainder allocation; ties broken by founder order; sums to ``total`` (T-003).

    ``ValueError`` when ``percents`` is empty, has a negative entry or does not sum to exactly
    100, or when ``total`` is negative.
    """
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")
    if not percents:
        raise ValueError("at least one percentage is required")
    exact_percents = [Fraction(p) for p in percents]
    if any(p < 0 for p in exact_percents):
        raise ValueError("percentages must not be negative")
    if sum(exact_percents) != _HUNDRED:
        raise ValueError(f"percentages must sum to exactly 100, got {float(sum(exact_percents))}")

    exact = [total * p / _HUNDRED for p in exact_percents]
    base = [int(x // 1) for x in exact]
    leftover = total - sum(base)  # 0 <= leftover < len(percents) because the fractions sum to an integer
    # Largest fractional part first; equal parts go to the earlier founder.
    order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:leftover]:
        base[i] += 1
    return base


def vesting_schedule(total: int, vesting_months: int, cliff_months: int, start: date) -> list[VestingEvent]:
    """Monthly vesting with a cliff, cumulative-floor so no share is lost (T-003).

    ``cum(k) = 0`` before the cliff, ``floor(total * k / vesting_months)`` from the cliff, and
    ``total`` at ``vesting_months``. Only months that vest something are returned; dates are
    ``add_months(start, month)``. ``vesting_months == 0`` vests everything at month 0.
    ``ValueError`` for a negative total or term, or a cliff longer than the vesting period.
    """
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")
    if vesting_months < 0 or cliff_months < 0:
        raise ValueError("vesting_months and cliff_months must be >= 0")
    if cliff_months > vesting_months:
        raise ValueError(f"cliff_months ({cliff_months}) must not exceed vesting_months ({vesting_months})")

    if vesting_months == 0:
        if total == 0:
            return []
        return [VestingEvent(month=0, date=start, vested_this_event=total, cumulative_vested=total)]

    def cum(k: int) -> int:
        if k < cliff_months:
            return 0
        if k >= vesting_months:
            return total
        return total * k // vesting_months

    events: list[VestingEvent] = []
    previous = 0
    for month in range(1, vesting_months + 1):
        current = cum(month)
        vested = current - previous
        if vested > 0:
            events.append(
                VestingEvent(month=month, date=add_months(start, month), vested_this_event=vested,
                             cumulative_vested=current)
            )
        previous = current
    return events
