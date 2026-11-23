"""Case validation, vesting defaults and missing facts (ADR-0013). Owned by T-002.

Validation is deterministic code, never the LLM. Every function here is pure: the input
``CaseFacts`` is never mutated; callers get a normalised copy back.

Issue ``field`` values (machine-facing, never shown in messages):

- ``founders`` for ``equity_total``;
- ``founders.name`` / ``founders.email`` / ``founders.equity_percent`` /
  ``founders.vesting_months`` / ``founders.cliff_months`` for per-founder issues, always with
  ``founder_id`` set;
- ``state`` for ``invalid_state`` and ``entity_state_mismatch``.

Issue order is deterministic: per-founder issues in founder order, then ``equity_total``,
then the state issues.
"""

from __future__ import annotations

import re
from decimal import Decimal

from ..domain.constants import DEFAULT_CLIFF_MONTHS, DEFAULT_VESTING_MONTHS, EQUITY_DECIMALS
from ..domain.states import US_STATES
from ..domain.types import CaseFacts, EntityType, Founder, ValidationIssue, ValidationResult

__all__ = ["ValidationIssue", "ValidationResult", "apply_vesting_defaults", "missing_facts", "validate_facts"]

MAX_VESTING_MONTHS = 120

# Required facts in the order the Manager asks for them (ADR-0013).
_REQUIRED_ORDER = ("business_description", "entity_type", "state", "founders", "incorporation_date")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")
_HUNDRED = Decimal(100)
_EQUITY_QUANTUM = Decimal(1).scaleb(-EQUITY_DECIMALS)  # Decimal("0.01") for 2 places
_FOUNDER_NUMBER = re.compile(r"^f(\d+)$")


# ---------------------------------------------------------------------------------------
# Small formatting helpers (messages are friendly sentences: no field codes, no JSON)
# ---------------------------------------------------------------------------------------
def _display_name(founder: Founder) -> str:
    name = " ".join((founder.name or "").split())
    if name:
        return name
    match = _FOUNDER_NUMBER.match(founder.id or "")
    return f"Founder {match.group(1)}" if match else "One of the founders"


def _possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _percent(value: Decimal) -> str:
    """``Decimal("90.00")`` -> ``"90"``, ``Decimal("33.50")`` -> ``"33.5"`` (never exponent form)."""
    if not value.is_finite():
        return str(value)
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "0") else text


def _months(n: int) -> str:
    return f"{n} month" if abs(n) == 1 else f"{n} months"


def _vesting_in_range(months: int) -> bool:
    return 0 <= months <= MAX_VESTING_MONTHS


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


# ---------------------------------------------------------------------------------------
# Vesting defaults
# ---------------------------------------------------------------------------------------
def apply_vesting_defaults(facts: CaseFacts) -> tuple[CaseFacts, list[str]]:
    """48/12 when both are missing, cliff ``min(12, vesting)`` or vesting 48 when one is; one
    founder-facing note per defaulted founder (ADR-0013, T-002).

    Returns a deep copy; ``facts`` itself is never changed. Founders whose vesting and cliff
    are both stated are left untouched and get no note.
    """
    data = facts.model_copy(deep=True)
    notes: list[str] = []
    founders: list[Founder] = []
    for founder in data.founders:
        vesting, cliff = founder.vesting_months, founder.cliff_months
        name = _display_name(founder)
        if vesting is None and cliff is None:
            vesting, cliff = DEFAULT_VESTING_MONTHS, DEFAULT_CLIFF_MONTHS
            notes.append(
                f"No vesting was given for {name}, so I used the standard "
                f"{DEFAULT_VESTING_MONTHS} months with a {DEFAULT_CLIFF_MONTHS}-month cliff."
            )
        elif cliff is None:
            cliff = min(DEFAULT_CLIFF_MONTHS, vesting)
            if _vesting_in_range(vesting):  # an impossible vesting is reported as an issue instead
                notes.append(
                    f"No cliff was given for {name}, so I used a {cliff}-month cliff "
                    f"with the {_months(vesting)} of vesting you gave."
                )
        elif vesting is None:
            vesting = DEFAULT_VESTING_MONTHS
            if cliff >= 0:  # a negative cliff is reported as an issue instead
                notes.append(
                    f"No vesting length was given for {name}, so I used the standard "
                    f"{DEFAULT_VESTING_MONTHS} months with the {cliff}-month cliff you gave."
                )
        else:
            founders.append(founder)
            continue
        founders.append(founder.model_copy(update={"vesting_months": vesting, "cliff_months": cliff}))
    data.founders = founders
    return data, notes


# ---------------------------------------------------------------------------------------
# Missing facts
# ---------------------------------------------------------------------------------------
def missing_facts(facts: CaseFacts) -> list[str]:
    """Required fact keys still unknown, in ask order: business_description, entity_type,
    state, founders, incorporation_date (ADR-0013, T-002).

    Blank strings count as unknown; ``founders`` is missing when the list is empty. Optional
    facts (``name_preferences``, ``website``, ``company_name``) are never listed.
    """
    present = {
        "business_description": not _blank(facts.business_description),
        "entity_type": facts.entity_type is not None,
        "state": not _blank(facts.state),
        "founders": bool(facts.founders),
        "incorporation_date": facts.incorporation_date is not None,
    }
    return [key for key in _REQUIRED_ORDER if not present[key]]


# ---------------------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------------------
def _founder_identity_issues(founders: list[Founder]) -> list[list[ValidationIssue]]:
    """Name, email and duplicate-email issues, one list per founder (same order)."""
    out: list[list[ValidationIssue]] = []
    seen_emails: dict[str, Founder] = {}
    for f in founders:
        issues: list[ValidationIssue] = []
        out.append(issues)
        name = _display_name(f)
        if _blank(f.name):
            issues.append(ValidationIssue(
                code="founder_name_missing", field="founders.name", founder_id=f.id,
                message=f"{name} needs a name. Please tell me their full legal name.",
            ))
        email = (f.email or "").strip()
        if not email:
            issues.append(ValidationIssue(
                code="founder_email_invalid", field="founders.email", founder_id=f.id,
                message=f"I still need an email address for {name}.",
            ))
            continue
        if not _EMAIL.match(email):
            issues.append(ValidationIssue(
                code="founder_email_invalid", field="founders.email", founder_id=f.id,
                message=f"\"{email}\" doesn't look like a valid email address for {name}. "
                        "Please check it.",
            ))
            continue
        key = email.casefold()
        first = seen_emails.get(key)
        if first is not None:
            issues.append(ValidationIssue(
                code="founder_email_duplicate", field="founders.email", founder_id=f.id,
                message=f"{name} has the same email address as {_display_name(first)}. "
                        "Each founder needs their own email address.",
            ))
        else:
            seen_emails[key] = f
    return out


def _equity_issues(f: Founder) -> list[ValidationIssue]:
    name = _display_name(f)
    value = f.equity_percent
    if not value.is_finite() or value <= 0 or value > _HUNDRED:
        return [ValidationIssue(
            code="equity_range", field="founders.equity_percent", founder_id=f.id,
            message=f"{_possessive(name)} equity is {_percent(value)}%. Each founder's share must be "
                    "more than 0% and no more than 100%.",
        )]
    if value != value.quantize(_EQUITY_QUANTUM):
        return [ValidationIssue(
            code="equity_precision", field="founders.equity_percent", founder_id=f.id,
            message=f"{_possessive(name)} equity of {_percent(value)}% has too many decimal places. "
                    f"Please use at most {EQUITY_DECIMALS} (for example 33.33%).",
        )]
    return []


def _vesting_issues(f: Founder) -> list[ValidationIssue]:
    """Expects vesting defaults already applied (both values set)."""
    name = _display_name(f)
    vesting, cliff = f.vesting_months, f.cliff_months
    if vesting is None or cliff is None:
        raise ValueError("vesting defaults must be applied before checking vesting")
    issues: list[ValidationIssue] = []
    if not _vesting_in_range(vesting):
        issues.append(ValidationIssue(
            code="vesting_range", field="founders.vesting_months", founder_id=f.id,
            message=f"{_possessive(name)} vesting period of {_months(vesting)} isn't possible. "
                    f"It must be between 0 and {MAX_VESTING_MONTHS} months.",
        ))
    elif cliff < 0:  # one range issue per founder: the vesting one explains it best
        issues.append(ValidationIssue(
            code="vesting_range", field="founders.cliff_months", founder_id=f.id,
            message=f"{_possessive(name)} cliff of {_months(cliff)} isn't possible. "
                    "A cliff can't be negative.",
        ))
    if not issues and cliff > vesting:
        if vesting == 0:
            detail = "With no vesting period the founder is fully vested at the start, so the cliff must be 0."
        else:
            detail = "The cliff can't be longer than the vesting period."
        issues.append(ValidationIssue(
            code="cliff_exceeds_vesting", field="founders.cliff_months", founder_id=f.id,
            message=f"{_possessive(name)} cliff of {_months(cliff)} is longer than their "
                    f"{_months(vesting)} of vesting. {detail}",
        ))
    return issues


def _equity_total_issue(founders: list[Founder]) -> ValidationIssue | None:
    if not founders:
        return None
    total = sum((f.equity_percent for f in founders), Decimal(0))
    if total.is_finite() and total == _HUNDRED:  # exact Decimal comparison, never float
        return None
    return ValidationIssue(
        code="equity_total", field="founders",
        message=f"Equity adds up to {_percent(total)}%; it must total exactly 100%.",
    )


def _state_issues(facts: CaseFacts) -> list[ValidationIssue]:
    state = facts.state
    if _blank(state):
        return []  # reported through missing_facts
    issues: list[ValidationIssue] = []
    if state not in US_STATES:
        issues.append(ValidationIssue(
            code="invalid_state", field="state",
            message=f"I don't recognise the state \"{state}\". Please use a US state code such as DE or WY.",
        ))
    if facts.entity_type == EntityType.C_CORP and state != "DE":
        where = US_STATES[state].name if state in US_STATES else f"\"{state}\""
        issues.append(ValidationIssue(
            code="entity_state_mismatch", field="state",
            message=f"A Delaware C-Corp has to be formed in Delaware, but the state is {where}. "
                    "Choose Delaware, or form an LLC instead.",
        ))
    return issues


def _normalise(facts: CaseFacts) -> CaseFacts:
    """Deep copy with the state code stripped and upper-cased (blank -> ``None``)."""
    data = facts.model_copy(deep=True)
    if data.state is not None:
        data.state = data.state.strip().upper() or None
    return data


# ---------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------
def validate_facts(facts: CaseFacts) -> ValidationResult:
    """Every ADR-0013 issue code plus missing facts and notes, on a normalised copy (T-002).

    Pure: ``facts`` is not mutated. ``result.facts`` has the state normalised and vesting
    defaults applied; ``ok`` is True only when there are no issues and nothing is missing.
    """
    normalised, notes = apply_vesting_defaults(_normalise(facts))

    issues: list[ValidationIssue] = []
    identity = _founder_identity_issues(normalised.founders)
    for f, identity_issues in zip(normalised.founders, identity):
        issues.extend(identity_issues)
        issues.extend(_equity_issues(f))
        issues.extend(_vesting_issues(f))
    total_issue = _equity_total_issue(normalised.founders)
    if total_issue is not None:
        issues.append(total_issue)
    issues.extend(_state_issues(normalised))

    missing = missing_facts(normalised)
    return ValidationResult(
        ok=not issues and not missing,
        issues=issues,
        missing=missing,
        facts=normalised,
        notes=notes,
    )
