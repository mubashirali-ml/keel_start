"""T-006 feature run: the Law Agent used the way the Manager and LegalService will use it.

FakeLLM (default handlers), a hand-built CapTable for the sample case, no network.
Run: bash scripts/py.sh evidence/T-006/feature_run.py   (recorded by scripts/record_run.sh T-006)
Prints the real inputs and outputs, asserts the key results, exits non-zero on failure.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from launch_agents.agents import AgentContext, AgentServices  # noqa: E402
from launch_agents.agents.law import LawAgent, draft_documents, spot_legal_issues  # noqa: E402
from launch_agents.domain import (  # noqa: E402
    LEGAL_NOTICE,
    AgentId,
    CapTable,
    CapTableRow,
    CaseFacts,
    CaseState,
    DocumentKind,
    EntityType,
    Founder,
    deadline_83b,
)
from launch_agents.llm import FakeLLM  # noqa: E402
from launch_agents.ports import FakeDomainChecker  # noqa: E402

TODAY = date(2026, 11, 23)
INCORPORATION = date(2026, 12, 1)
FAILURES: list[str] = []


def check(condition: bool, what: str) -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {what}")
    if not condition:
        FAILURES.append(what)


def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def context(facts: CaseFacts, text: str, llm: FakeLLM, state: CaseState) -> AgentContext:
    return AgentContext(case_id="case_demo", facts=facts, state=state, history=[], founder_text=text,
                        founder_id="f1", today=TODAY, llm=llm,
                        services=AgentServices(domain_checker=FakeDomainChecker()))


def cap_table_for(facts: CaseFacts, rows: list[tuple[int, int, int]]) -> CapTable:
    """Hand-built cap table (the Law Agent never computes shares; T-003 builds the real one)."""
    return CapTable(
        entity_type=facts.entity_type,
        unit_label="units" if facts.entity_type == EntityType.LLC else "shares",
        vesting_start=facts.incorporation_date,
        rows=[CapTableRow(founder_id=f.id, name=f.name, email=f.email, equity_percent=f.equity_percent,
                          shares=shares, vesting_months=v, cliff_months=c, schedule=[])
              for f, (shares, v, c) in zip(facts.founders, rows)],
        total_issued=sum(r[0] for r in rows),
    )


_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+|[A-Za-z]+")


def numbers_next_to_shares(content: str) -> list[int]:
    tokens = _TOKEN.findall(content)
    found = []
    for i, token in enumerate(tokens):
        if token.lower() in {"share", "shares", "unit", "units"}:
            for j in (i - 2, i - 1, i + 1, i + 2):
                if 0 <= j < len(tokens) and tokens[j][0].isdigit():
                    found.append(int(tokens[j].replace(",", "")))
    return found


# --- the sample case ----------------------------------------------------------------------
sample = CaseFacts(
    business_description="bookkeeping software for small bakeries",
    founders=[
        Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("60"),
                vesting_months=48, cliff_months=12),
        Founder(id="f2", name="Bob Diaz", email="bob@example.com", equity_percent=Decimal("40"),
                vesting_months=48, cliff_months=12),  # the 48/12 default, already applied
    ],
    entity_type=EntityType.LLC,
    state="WY",
    incorporation_date=INCORPORATION,
)
unequal = sample.model_copy(update={"founders": [
    sample.founders[0], sample.founders[1].model_copy(update={"vesting_months": 24, "cliff_months": 6})]})

banner("1. Issue spotting")
print(f"today={TODAY}  incorporation={INCORPORATION}  83(b) deadline={deadline_83b(INCORPORATION)}")
clean = spot_legal_issues(sample, CaseState(), TODAY)
print(f"clean sample -> {[i.code for i in clean]}")
check(clean == [], "no issues for the clean sample")
spotted = spot_legal_issues(unequal, CaseState(), TODAY)
for issue in spotted:
    print(f"unequal facts -> {issue.code} ({issue.severity}): {issue.message}")
check([i.code for i in spotted] == ["unequal_vesting"], "unequal vesting is spotted")
late = spot_legal_issues(sample, CaseState(), date(2026, 12, 27))
print(f"on 2026-12-27 -> {[(i.code, i.message) for i in late]}")
check([i.code for i in late] == ["deadline_83b_soon"], "83(b) deadline 4 days away is flagged")

# --- three questions ----------------------------------------------------------------------
llm = FakeLLM()
agent = LawAgent()
questions = [
    ("LLC or C-Corp?", sample),
    ("what is an 83(b)?", sample),
    ("is unequal vesting a problem?", unequal),
]
for n, (question, facts) in enumerate(questions, start=2):
    banner(f"{n}. Founder asks: {question!r}")
    reply = agent.handle(context(facts, question, llm, CaseState(active_agent=AgentId.LAW)))
    message = reply.messages[0]
    print(f"[{message.agent.value} / {message.kind.value}] hand_back={reply.hand_back} actions={reply.actions}")
    print(message.content)
    print(f"state.legal_issues = {[i.code for i in reply.state.legal_issues]}")
    check(len(reply.messages) == 1 and message.agent == AgentId.LAW, "one message from the Law Agent")
    check(message.content.endswith(LEGAL_NOTICE), "ends with the legal notice")
    check(reply.hand_back is False and reply.actions == [], "keeps the conversation, no actions")
    if question.startswith("LLC"):
        check("LLC" in message.content and "Delaware C-Corp" in message.content, "explains LLC vs C-Corp")
    if "83(b)" in question:
        check("December 31, 2026" in message.content, "names this case's 83(b) deadline")
    if "unequal" in question:
        check(spotted[0].message in message.content, "mentions the unequal-vesting issue it spotted")
        check([i.code for i in reply.state.legal_issues] == ["unequal_vesting"], "state.legal_issues updated")
print(f"\nLLM tasks called: {[c.task for c in llm.calls]}")

# --- drafting requests --------------------------------------------------------------------
banner("5. Founder asks to draft documents before the facts are confirmed")
reply = agent.handle(context(sample, "Please draft our documents", llm, CaseState(active_agent=AgentId.LAW)))
print(reply.messages[0].content)
print(f"actions={reply.actions} hand_back={reply.hand_back}")
check(reply.actions == [] and reply.hand_back is True, "no action, hands back to the Manager")
check("Manager" in reply.messages[0].content, "explains the Manager must confirm the facts first")

banner("6. Same request with locked facts")
reply = agent.handle(context(sample, "Please draft our documents", llm,
                             CaseState(active_agent=AgentId.LAW, facts_locked=True)))
print(reply.messages[0].content)
print(f"actions={[a.model_dump() for a in reply.actions]} hand_back={reply.hand_back}")
check([a.type for a in reply.actions] == ["draft_documents", "open_view"], "DraftDocuments + OpenView")
check(reply.actions[1].view == "legal" and reply.hand_back is True, "opens the legal view, hands back")


# --- drafting ----------------------------------------------------------------------------
def show_documents(label: str, facts: CaseFacts, cap: CapTable, expected_kinds: list[DocumentKind]) -> None:
    banner(label)
    print(f"cap table ({cap.unit_label}): " + ", ".join(f"{r.name} {r.shares:,}" for r in cap.rows))
    docs = draft_documents(facts, cap, TODAY)
    rows = {r.founder_id: r for r in cap.rows}
    for doc in docs:
        print(f"\n--- {doc.title}  [{doc.kind.value}]  signers={doc.required_signers}")
        for line in [ln for ln in doc.content.splitlines() if ln.strip()][:6]:
            print(f"    {line}")
        keys = ("Date of transfer", "Property:", "Restrictions:", "no later than") \
            if doc.kind == DocumentKind.ELECTION_83B else ("ownership):",)
        for line in [ln for ln in doc.content.splitlines() if any(k in ln for k in keys)]:
            print(f"    ... {line}")
        found = sorted(set(numbers_next_to_shares(doc.content)))
        allowed = sorted({rows[doc.founder_id].shares} if doc.founder_id else {r.shares for r in cap.rows})
        print(f"    numbers next to shares/units: {found}  (cap table: {allowed})")
        check(found == allowed, f"{doc.title}: share counts match the cap table")
        check(doc.content.startswith(LEGAL_NOTICE) and doc.content.endswith(LEGAL_NOTICE),
              f"{doc.title}: notice at start and end")
        check(all(p in doc.content for p in ("[ADDRESS]", "[TAXPAYER ID]", "[FAIR MARKET VALUE PER SHARE]")),
              f"{doc.title}: placeholders kept")
        if doc.kind == DocumentKind.ELECTION_83B:
            check(doc.required_signers == [doc.founder_id], f"{doc.title}: signed by that founder only")
            check("December 1, 2026" in doc.content and "December 31, 2026" in doc.content,
                  f"{doc.title}: transfer date and filing deadline stated")
        else:
            check(doc.required_signers == [r.founder_id for r in cap.rows], f"{doc.title}: all founders sign")
    check([d.kind for d in docs] == expected_kinds, "the right documents, in order")


show_documents(
    "7. Drafting the LLC set (sample case, no company name chosen yet)",
    sample,
    cap_table_for(sample, [(6_000_000, 48, 12), (4_000_000, 48, 12)]),
    [DocumentKind.IP_ASSIGNMENT, DocumentKind.OPERATING_AGREEMENT_SUMMARY,
     DocumentKind.ELECTION_83B, DocumentKind.ELECTION_83B],
)
check("[COMPANY NAME]" in draft_documents(sample, cap_table_for(sample, [(6_000_000, 48, 12), (4_000_000, 48, 12)]),
                                          TODAY)[0].content, "LLC set uses [COMPANY NAME]")

ccorp = CaseFacts(
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
show_documents(
    "8. Drafting a Delaware C-Corp set (Molar Labs Inc., three founders)",
    ccorp,
    cap_table_for(ccorp, [(3_333_300, 48, 12), (3_333_300, 36, 0), (3_333_400, 0, 0)]),
    [DocumentKind.IP_ASSIGNMENT, DocumentKind.BYLAWS_SUMMARY,
     DocumentKind.ELECTION_83B, DocumentKind.ELECTION_83B, DocumentKind.ELECTION_83B],
)

banner("Result")
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed:")
    for failure in FAILURES:
        print(f"  - {failure}")
    sys.exit(1)
print("all checks passed")
