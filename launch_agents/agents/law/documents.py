"""Founding-document drafting (ADR-0014). Owned by T-006.

``draft_documents`` fills the Markdown templates in ``templates/``. Share/unit counts are
quoted **only** from ``cap_table.rows[i].shares`` (ADR-0013: this module never computes
shares), and no other number is ever written next to the words "shares" or "units".
Details the app does not know (or never stores, ADR-0033) stay as bracketed placeholders.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from string import Template

from ...domain.cap_table import CapTable, CapTableRow
from ...domain.constants import LEGAL_NOTICE
from ...domain.documents import DocumentKind, DraftDocument
from ...domain.errors import FactsNotReadyError, InvalidStateError
from ...domain.helpers import add_months, deadline_83b
from ...domain.states import state_info
from ...domain.types import CaseFacts, EntityType
from .issues import format_date, vesting_phrase

__all__ = [
    "BYLAWS_TITLE",
    "COMPANY_NAME_PLACEHOLDER",
    "IP_ASSIGNMENT_TITLE",
    "OPERATING_AGREEMENT_TITLE",
    "draft_documents",
    "election_83b_title",
]

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

COMPANY_NAME_PLACEHOLDER = "[COMPANY NAME]"
IP_ASSIGNMENT_TITLE = "Founder IP Assignment Agreement"
BYLAWS_TITLE = "Bylaws Summary"
OPERATING_AGREEMENT_TITLE = "Operating Agreement Summary"


def election_83b_title(founder_name: str) -> str:
    """``"IRS 83(b) Election — Alice Chen"`` (ADR-0014)."""
    return f"IRS 83(b) Election — {founder_name}"


@lru_cache(maxsize=None)
def _template(name: str) -> Template:
    text = (TEMPLATES_DIR / f"{name}.md").read_text(encoding="utf-8")
    return Template(text.replace("\r\n", "\n").replace("\r", "\n"))


def _render(name: str, **values: str) -> str:
    content = _template(name).substitute(notice=LEGAL_NOTICE, **values).strip()
    # The contract (ADR-0014): every document starts and ends with the notice.
    assert content.startswith(LEGAL_NOTICE) and content.endswith(LEGAL_NOTICE)
    return content


def _percent(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return f"{text}%"


def _count(row: CapTableRow, unit_label: str) -> str:
    return f"{row.shares:,} {unit_label}"


def _fully_vested_on(row: CapTableRow, start: date) -> date:
    return add_months(start, row.vesting_months)


def _vesting_terms(row: CapTableRow, start: date) -> str:
    """Plain words for one founder's schedule (never mentions a share count)."""
    if row.vesting_months == 0:
        return f"fully vested on {format_date(start)}, with no vesting schedule"
    fully = format_date(_fully_vested_on(row, start))
    if row.cliff_months == 0:
        return (f"monthly over {row.vesting_months} months starting {format_date(start)}, "
                f"with no cliff; fully vested on {fully}")
    return (f"monthly over {row.vesting_months} months starting {format_date(start)}, with a "
            f"{row.cliff_months}-month cliff (nothing vests before the cliff, the accrued part "
            f"vests at the cliff, then the rest monthly); fully vested on {fully}")


def _check_inputs(facts: CaseFacts, cap_table: CapTable) -> EntityType:
    entity = facts.entity_type or cap_table.entity_type
    if entity != cap_table.entity_type:
        raise FactsNotReadyError(
            "The cap table was built for a different entity type. Rebuild the cap table before drafting documents.",
            details={"facts_entity_type": entity.value, "cap_table_entity_type": cap_table.entity_type.value},
        )
    if not cap_table.rows:
        raise FactsNotReadyError("Add at least one founder before drafting documents.")
    fact_ids = [f.id for f in facts.founders]
    row_ids = [r.founder_id for r in cap_table.rows]
    if fact_ids and fact_ids != row_ids:
        raise FactsNotReadyError(
            "The cap table doesn't match the current founders. Rebuild the cap table before drafting documents.",
            details={"founders": fact_ids, "cap_table": row_ids},
        )
    return entity


def _state_name(code: str | None) -> str:
    if not code:
        return "[STATE]"
    try:
        return state_info(code).name
    except InvalidStateError:
        return "[STATE]"


def draft_documents(facts: CaseFacts, cap_table: CapTable, today: date) -> list[DraftDocument]:
    """IP assignment, bylaws / operating agreement summary and one 83(b) per founder, as
    Markdown starting and ending with ``LEGAL_NOTICE``; share counts only from ``cap_table``
    (ADR-0014, T-006).

    Order: Founder IP Assignment Agreement; Bylaws Summary (C-Corp) or Operating Agreement
    Summary (LLC); then ``IRS 83(b) Election — {founder}`` per cap-table row. IP and summary
    are signed by every founder; each 83(b) only by its founder. Raises
    ``FactsNotReadyError`` when the cap table does not fit the facts.
    """
    entity = _check_inputs(facts, cap_table)
    is_llc = entity == EntityType.LLC
    unit_label = cap_table.unit_label
    unit_singular = "unit" if unit_label == "units" else "share"
    start = facts.incorporation_date or cap_table.vesting_start
    state_code = "DE" if entity == EntityType.C_CORP else facts.state
    state_name = _state_name(state_code)
    entity_long = f"{state_name} limited liability company" if is_llc else f"{state_name} corporation"
    company = facts.company_name.strip() if facts.company_name and facts.company_name.strip() else COMPANY_NAME_PLACEHOLDER
    business = (facts.business_description or "").strip() or "[BUSINESS DESCRIPTION]"
    emails = {f.id: f.email for f in facts.founders}
    all_signers = [row.founder_id for row in cap_table.rows]
    stock_words = "membership units" if is_llc else "shares of common stock"

    common = {
        "company": company,
        "entity_long": entity_long,
        "state_name": state_name,
        "business": business,
        "effective_date": format_date(start),
        "prepared_date": format_date(today),
        "unit_label": unit_label,
        "unit_singular": unit_singular,
    }
    founder_parties = "\n".join(
        f"- Founder: {row.name}"
        + (f" ({emails[row.founder_id]})" if emails.get(row.founder_id) else "")
        + ", address [ADDRESS]"
        for row in cap_table.rows
    )
    equity_lines = "\n".join(
        f"- {row.name} ({_percent(row.equity_percent)} ownership): {_count(row, unit_label)}."
        for row in cap_table.rows
    )
    vesting_lines = "\n".join(f"- {row.name}: {_vesting_terms(row, start)}." for row in cap_table.rows)
    role = "Member" if is_llc else "Founder"
    summary_signatures = "\n".join(f"- {row.name}, {role}: signature recorded in the app" for row in cap_table.rows)
    ip_signatures = "\n".join(f"- {row.name}, Founder: signature recorded in the app" for row in cap_table.rows)

    docs = [
        DraftDocument(
            kind=DocumentKind.IP_ASSIGNMENT,
            title=IP_ASSIGNMENT_TITLE,
            founder_id=None,
            content=_render("ip_assignment", **common, founder_parties=founder_parties,
                            equity_lines=equity_lines, signature_lines=ip_signatures),
            required_signers=list(all_signers),
        ),
        DraftDocument(
            kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY if is_llc else DocumentKind.BYLAWS_SUMMARY,
            title=OPERATING_AGREEMENT_TITLE if is_llc else BYLAWS_TITLE,
            founder_id=None,
            content=_render("operating_agreement_summary" if is_llc else "bylaws_summary", **common,
                            equity_lines=equity_lines, vesting_lines=vesting_lines,
                            signature_lines=summary_signatures),
            required_signers=list(all_signers),
        ),
    ]
    deadline = format_date(deadline_83b(start))
    for row in cap_table.rows:
        shares_text = f"{row.shares:,} {stock_words}"
        docs.append(DraftDocument(
            kind=DocumentKind.ELECTION_83B,
            title=election_83b_title(row.name),
            founder_id=row.founder_id,
            content=_render("election_83b", **common, founder_name=row.name,
                            transfer_date=format_date(start), tax_year=str(start.year),
                            shares_text=shares_text, vesting_terms=_vesting_terms(row, start),
                            deadline=deadline),
            required_signers=[row.founder_id],
        ))
    return docs
