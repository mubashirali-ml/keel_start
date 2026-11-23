"""T-006: founding-document drafting (ADR-0014, ADR-0013). Cap tables are built by hand:
the Law Agent quotes ``cap_table.rows[i].shares`` and never computes shares."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest

from launch_agents.agents.law import draft_documents
from launch_agents.agents.law.documents import COMPANY_NAME_PLACEHOLDER, election_83b_title
from launch_agents.agents.law.issues import format_date
from launch_agents.domain import (
    LEGAL_NOTICE,
    CapTable,
    CapTableRow,
    CaseFacts,
    DocumentKind,
    EntityType,
    FactsNotReadyError,
    Founder,
    deadline_83b,
)

TODAY = date(2026, 11, 23)
INCORPORATION = date(2026, 12, 1)


def _row(founder: Founder, shares: int, vesting: int, cliff: int) -> CapTableRow:
    return CapTableRow(founder_id=founder.id, name=founder.name, email=founder.email,
                       equity_percent=founder.equity_percent, shares=shares, vesting_months=vesting,
                       cliff_months=cliff, schedule=[])


def _cap(facts: CaseFacts, rows: list[tuple[int, int, int]]) -> CapTable:
    entity = facts.entity_type
    return CapTable(
        entity_type=entity,
        unit_label="units" if entity == EntityType.LLC else "shares",
        vesting_start=facts.incorporation_date,
        rows=[_row(f, *r) for f, r in zip(facts.founders, rows)],
        total_issued=sum(r[0] for r in rows),
    )


@pytest.fixture
def llc(sample_facts):
    # Sample: Alice 60 % 48/12, Bob 40 % (defaults 48/12) -> 6,000,000 / 4,000,000 units.
    return sample_facts, _cap(sample_facts, [(6_000_000, 48, 12), (4_000_000, 48, 12)])


@pytest.fixture
def ccorp():
    facts = CaseFacts(
        business_description="AI scheduling for dental clinics",
        founders=[
            Founder(id="f1", name="Dana Park", email="dana@example.com", equity_percent=Decimal("33.33"),
                    vesting_months=48, cliff_months=12),
            Founder(id="f2", name="Eli Stone", email="eli@example.com", equity_percent=Decimal("33.33"),
                    vesting_months=36, cliff_months=0),
            Founder(id="f3", name="Fay Wu", email="fay@example.com", equity_percent=Decimal("33.34"),
                    vesting_months=0, cliff_months=0),
        ],
        entity_type=EntityType.C_CORP,
        state="DE",
        incorporation_date=INCORPORATION,
        company_name="Molar Labs Inc.",
    )
    return facts, _cap(facts, [(3_333_300, 48, 12), (3_333_300, 36, 0), (3_333_400, 0, 0)])


_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+|[A-Za-z]+")
_UNIT_WORDS = {"share", "shares", "unit", "units"}


def numbers_next_to_shares(content: str) -> list[int]:
    """Every integer within two words of "shares"/"units" (e.g. "6,000,000 membership units",
    "Shares: 6,000,000")."""
    tokens = _TOKEN.findall(content)
    found: list[int] = []
    for i, token in enumerate(tokens):
        if token.lower() not in _UNIT_WORDS:
            continue
        for j in (i - 2, i - 1, i + 1, i + 2):
            if 0 <= j < len(tokens) and tokens[j][0].isdigit():
                found.append(int(tokens[j].replace(",", "")))
    return found


def thousands_numbers(content: str) -> list[int]:
    return [int(m.replace(",", "")) for m in re.findall(r"\b\d{1,3}(?:,\d{3})+\b", content)]


# --- criterion 4: which documents, titles, signers ---------------------------------------
def test_ccorp_documents_titles_and_signers(ccorp):
    facts, cap = ccorp
    docs = draft_documents(facts, cap, TODAY)
    assert [d.kind for d in docs] == [DocumentKind.IP_ASSIGNMENT, DocumentKind.BYLAWS_SUMMARY,
                                     DocumentKind.ELECTION_83B, DocumentKind.ELECTION_83B,
                                     DocumentKind.ELECTION_83B]
    assert [d.title for d in docs] == [
        "Founder IP Assignment Agreement", "Bylaws Summary",
        "IRS 83(b) Election — Dana Park", "IRS 83(b) Election — Eli Stone", "IRS 83(b) Election — Fay Wu",
    ]
    assert docs[0].required_signers == docs[1].required_signers == ["f1", "f2", "f3"]
    assert docs[0].founder_id is None and docs[1].founder_id is None
    for doc, fid in zip(docs[2:], ["f1", "f2", "f3"]):
        assert doc.founder_id == fid
        assert doc.required_signers == [fid]  # that founder only (ADR-0014, Q-001)


def test_llc_gets_operating_agreement_summary(llc):
    facts, cap = llc
    docs = draft_documents(facts, cap, TODAY)
    assert [d.kind for d in docs] == [DocumentKind.IP_ASSIGNMENT, DocumentKind.OPERATING_AGREEMENT_SUMMARY,
                                     DocumentKind.ELECTION_83B, DocumentKind.ELECTION_83B]
    assert [d.title for d in docs] == ["Founder IP Assignment Agreement", "Operating Agreement Summary",
                                      election_83b_title("Alice Chen"), election_83b_title("Bob Diaz")]
    assert all(d.kind != DocumentKind.BYLAWS_SUMMARY for d in docs)
    assert docs[0].required_signers == docs[1].required_signers == ["f1", "f2"]
    assert [d.required_signers for d in docs[2:]] == [["f1"], ["f2"]]
    assert "Wyoming limited liability company" in docs[1].content


# --- criterion 5: notice, placeholders, share counts --------------------------------------
@pytest.mark.parametrize("which", ["llc", "ccorp"])
def test_every_document_starts_and_ends_with_notice_and_keeps_placeholders(which, request):
    facts, cap = request.getfixturevalue(which)
    for doc in draft_documents(facts, cap, TODAY):
        assert doc.content.startswith(LEGAL_NOTICE), doc.title
        assert doc.content.endswith(LEGAL_NOTICE), doc.title
        for placeholder in ("[ADDRESS]", "[TAXPAYER ID]", "[FAIR MARKET VALUE PER SHARE]"):
            assert placeholder in doc.content, (doc.title, placeholder)
        assert "$" not in doc.content and "${" not in doc.content  # every template field was filled
        assert "|" not in doc.content  # stays inside the Markdown subset the PDF renderer reads (ADR-0031)


def test_company_name_placeholder_when_no_name_chosen(llc):
    facts, cap = llc
    assert facts.company_name is None
    assert COMPANY_NAME_PLACEHOLDER == "[COMPANY NAME]"
    for doc in draft_documents(facts, cap, TODAY):
        assert "[COMPANY NAME]" in doc.content, doc.title


def test_chosen_company_name_is_used(ccorp):
    facts, cap = ccorp
    for doc in draft_documents(facts, cap, TODAY):
        assert "Molar Labs Inc." in doc.content
        assert "[COMPANY NAME]" not in doc.content


@pytest.mark.parametrize("which", ["llc", "ccorp"])
def test_share_counts_equal_the_cap_table(which, request):
    facts, cap = request.getfixturevalue(which)
    rows = {r.founder_id: r.shares for r in cap.rows}
    for doc in draft_documents(facts, cap, TODAY):
        found = numbers_next_to_shares(doc.content)
        allowed = {rows[doc.founder_id]} if doc.founder_id else set(rows.values())
        assert found, doc.title
        assert set(found) <= allowed, (doc.title, found)
        assert set(found) == allowed, (doc.title, found)
        assert set(thousands_numbers(doc.content)) <= allowed  # no other big number anywhere


def test_share_counts_are_quoted_not_computed(llc):
    facts, _ = llc
    # Deliberately "odd" counts: a drafter that recomputed from percentages would print 6,000,000.
    cap = _cap(facts, [(6_000_001, 48, 12), (3_999_999, 48, 12)])
    docs = draft_documents(facts, cap, TODAY)
    assert "6,000,001 units" in docs[0].content and "3,999,999 units" in docs[0].content
    assert "6,000,000" not in docs[0].content
    assert numbers_next_to_shares(docs[3].content) and set(numbers_next_to_shares(docs[3].content)) == {3_999_999}


# --- criterion 6: the 83(b) form ----------------------------------------------------------
def test_83b_states_transfer_date_deadline_shares_and_vesting(ccorp):
    facts, cap = ccorp
    docs = {d.founder_id: d for d in draft_documents(facts, cap, TODAY) if d.kind == DocumentKind.ELECTION_83B}
    deadline = deadline_83b(INCORPORATION)
    assert deadline == date(2026, 12, 31)
    for row in cap.rows:
        content = docs[row.founder_id].content
        assert f"Date of transfer: {format_date(INCORPORATION)}" in content
        assert "December 1, 2026" in content
        assert format_date(deadline) in content and "December 31, 2026" in content
        assert f"{row.shares:,} shares of common stock" in content
        assert row.name in content
    assert "over 48 months" in docs["f1"].content and "12-month cliff" in docs["f1"].content
    assert "fully vested on December 1, 2030" in docs["f1"].content
    assert "over 36 months" in docs["f2"].content and "no cliff" in docs["f2"].content
    assert "fully vested on December 1, 2026, with no vesting schedule" in docs["f3"].content
    assert "[SPOUSE NAME, IF ANY]" in docs["f1"].content


def test_llc_83b_uses_units(llc):
    facts, cap = llc
    election = draft_documents(facts, cap, TODAY)[2]
    assert "6,000,000 membership units" in election.content
    assert "shares" not in election.content.lower().replace("per share]", "")


def test_bylaws_list_every_founder_with_vesting(ccorp):
    facts, cap = ccorp
    bylaws = draft_documents(facts, cap, TODAY)[1]
    for row in cap.rows:
        assert f"{row.name} ({row.equity_percent}% ownership): {row.shares:,} shares." in bylaws.content
    assert "Delaware corporation" in bylaws.content
    assert "[REGISTERED AGENT]" in bylaws.content


def test_drafting_is_deterministic(ccorp):
    facts, cap = ccorp
    assert draft_documents(facts, cap, TODAY) == draft_documents(facts, cap, TODAY)


def test_cap_table_that_does_not_fit_the_facts_is_rejected(llc, ccorp):
    facts, cap = llc
    with pytest.raises(FactsNotReadyError):
        draft_documents(facts, ccorp[1], TODAY)  # C-Corp cap table for an LLC case
    other = facts.model_copy(update={"founders": facts.founders[:1]})
    with pytest.raises(FactsNotReadyError):
        draft_documents(other, cap, TODAY)  # founders changed since the cap table was built
