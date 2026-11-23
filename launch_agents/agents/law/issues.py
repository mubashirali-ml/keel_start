"""Deterministic legal issue spotting (ADR-0009, ADR-0013). Owned by T-006.

Codes (T-006 criterion 1), in the order they are returned:

| code | severity | when |
|---|---|---|
| ``unequal_vesting`` | info | founders are on different (vesting, cliff) schedules |
| ``no_cliff`` | info | a founder has ``cliff_months == 0`` and ``vesting_months > 0`` (one per founder) |
| ``name_conflict`` | warning | the chosen name's ``.com`` is taken; with no name chosen yet, the candidates whose ``.com`` is taken (one issue listing them) |
| ``deadline_83b_soon`` | warning | 0..7 days left until the 83(b) deadline |
| ``deadline_83b_passed`` | warning | the 83(b) deadline has passed |

Vesting is compared after the ADR-0013 defaults, so a founder with no vesting stated counts
as 48/12 (the defaults are re-stated here because ``rules.validation`` belongs to T-002).
"""

from __future__ import annotations

from datetime import date

from ...domain.constants import DEFAULT_CLIFF_MONTHS, DEFAULT_VESTING_MONTHS
from ...domain.helpers import days_until, deadline_83b, domain_label, names_match
from ...domain.state import CaseState, DomainStatus, LegalIssue, NameCandidate
from ...domain.types import CaseFacts, Founder

__all__ = ["format_date", "resolved_vesting", "spot_legal_issues", "vesting_phrase"]


def format_date(d: date) -> str:
    """``date(2026, 12, 31)`` -> ``"December 31, 2026"``."""
    return f"{d:%B} {d.day}, {d.year}"


def resolved_vesting(founder: Founder) -> tuple[int, int]:
    """(vesting_months, cliff_months) after the ADR-0013 defaults."""
    vesting, cliff = founder.vesting_months, founder.cliff_months
    if vesting is None and cliff is None:
        return DEFAULT_VESTING_MONTHS, DEFAULT_CLIFF_MONTHS
    if vesting is None:
        return DEFAULT_VESTING_MONTHS, int(cliff)  # type: ignore[arg-type]
    if cliff is None:
        return vesting, min(DEFAULT_CLIFF_MONTHS, vesting)
    return vesting, cliff


def vesting_phrase(vesting_months: int, cliff_months: int) -> str:
    """Plain words for a schedule: ``"48 months with a 12-month cliff"``."""
    if vesting_months == 0:
        return "fully vested from the start"
    if cliff_months == 0:
        return f"{vesting_months} months with no cliff"
    return f"{vesting_months} months with a {cliff_months}-month cliff"


def _dot_com_taken(candidate: NameCandidate) -> str | None:
    """The candidate's taken ``.com`` domain, if it has one."""
    for check in candidate.domains:
        if check.domain.lower().endswith(".com") and check.status == DomainStatus.TAKEN:
            return check.domain
    return None


def _chosen_name_taken_domain(name: str, candidates: list[NameCandidate]) -> str | None:
    for candidate in candidates:
        if names_match(candidate.name, name):
            return _dot_com_taken(candidate)
    wanted = f"{domain_label(name)}.com"
    for candidate in candidates:
        for check in candidate.domains:
            if check.domain.lower() == wanted and check.status == DomainStatus.TAKEN:
                return check.domain
    return None


def _vesting_issues(facts: CaseFacts) -> list[LegalIssue]:
    issues: list[LegalIssue] = []
    schedules = [(f, *resolved_vesting(f)) for f in facts.founders]
    if len({(v, c) for _, v, c in schedules}) > 1:
        detail = "; ".join(f"{f.name}: {vesting_phrase(v, c)}" for f, v, c in schedules)
        issues.append(LegalIssue(
            code="unequal_vesting",
            severity="info",
            message=(
                f"Your founders are on different vesting schedules ({detail}). That is allowed, "
                "but make sure everyone agrees to it, because it changes how much equity each "
                "founder keeps if they leave early."
            ),
        ))
    for founder, vesting, cliff in schedules:
        if cliff == 0 and vesting > 0:
            issues.append(LegalIssue(
                code="no_cliff",
                severity="info",
                message=(
                    f"{founder.name} has no vesting cliff, so their equity starts vesting in the "
                    "first month. That is allowed, but most startups use a 12-month cliff so a "
                    "founder who leaves very early doesn't keep part of the company."
                ),
            ))
    return issues


def _name_issues(facts: CaseFacts, state: CaseState) -> list[LegalIssue]:
    if facts.company_name:
        taken = _chosen_name_taken_domain(facts.company_name, state.name_candidates)
        if taken is None:
            return []
        return [LegalIssue(
            code="name_conflict",
            severity="warning",
            message=(
                f"The .com domain for your chosen name \"{facts.company_name}\" ({taken}) is already "
                "taken. Someone may already be using this name, so check the state business-name "
                "search and the USPTO trademark search before you rely on it."
            ),
        )]
    taken_names = [c.name for c in state.name_candidates if _dot_com_taken(c)]
    if not taken_names:
        return []
    listed = ", ".join(f"\"{n}\"" for n in taken_names)
    return [LegalIssue(
        code="name_conflict",
        severity="warning",
        message=(
            f"The .com domain is already taken for {listed}. Someone may already be using "
            f"{'that name' if len(taken_names) == 1 else 'those names'}, so check the state "
            "business-name search and the USPTO trademark search before you pick one."
        ),
    )]


def _deadline_issues(facts: CaseFacts, today: date) -> list[LegalIssue]:
    if facts.incorporation_date is None:
        return []
    deadline = deadline_83b(facts.incorporation_date)
    left = days_until(deadline, today)
    when = format_date(deadline)
    if left < 0:
        return [LegalIssue(
            code="deadline_83b_passed",
            severity="warning",
            message=(
                f"The 83(b) election deadline ({when}) has passed. The IRS does not accept late "
                "83(b) elections, so please talk to a tax adviser or attorney about your options."
            ),
        )]
    if left <= 7:
        if left == 0:
            soon = "that is today"
        elif left == 1:
            soon = "only 1 day away"
        else:
            soon = f"only {left} days away"
        return [LegalIssue(
            code="deadline_83b_soon",
            severity="warning",
            message=(
                f"Your 83(b) election deadline is {when}, {soon}. Each founder who wants to make "
                "the election must mail it to the IRS by then, so file as early as you can."
            ),
        )]
    return []


def spot_legal_issues(facts: CaseFacts, state: CaseState, today: date) -> list[LegalIssue]:
    """Info/warning issues the Law Agent points out, in a fixed order (see module doc).
    Pure: the same facts, state and day give the same issues."""
    return [*_vesting_issues(facts), *_name_issues(facts, state), *_deadline_issues(facts, today)]
