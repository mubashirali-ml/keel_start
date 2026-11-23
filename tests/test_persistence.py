"""T-005: the case Repository on a real SQLite file (and PostgreSQL when
``LAUNCH_TEST_POSTGRES_URL`` is set): cases, messages, documents with versions and
e-signature evidence, audit, checklist, site builds, cascade delete and transactions."""

from __future__ import annotations

import os
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import BaseModel
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError

from launch_agents.domain.documents import (
    AuditAction,
    AuditEntry,
    Document,
    DocumentKind,
    DocumentStatus,
    Signature,
)
from launch_agents.domain.constants import ESIGN_CONSENT_VERSION
from launch_agents.domain.errors import ConflictError, NotFoundError, StaleVersionError
from launch_agents.domain.helpers import document_sha256
from launch_agents.domain.messages import (
    AgentId,
    ChatMessage,
    MessageKind,
    MessageRole,
    SuggestedReply,
    agent_message,
    handoff_message,
)
from launch_agents.domain.state import CaseRecord, CaseState, DomainCheck, DomainStatus, LegalIssue, NameCandidate
from launch_agents.domain.types import CaseFacts, EntityType, Founder, WebsiteRequirements
from launch_agents.domain.website import (
    QaCheckId,
    QaCheckResult,
    QaIssue,
    QaReport,
    SiteBuild,
    SiteBuildStatus,
    SiteBundle,
    SiteContact,
    SiteContent,
    SiteFile,
    SiteFounder,
    SitePage,
    SiteSection,
)
from launch_agents.persistence import repository as repository_module
from launch_agents.persistence import tables
from launch_agents.persistence.engine import create_db_engine, init_db
from launch_agents.persistence.repository import Repository

T0 = datetime(2026, 11, 23, 9, 0, 0, 123456, tzinfo=timezone.utc)
CASE_OWNED_TABLES = ("messages", "documents", "document_versions", "signatures", "checklist_items",
                     "site_builds", "audit_log")


# ---------------------------------------------------------------------------------------
# fixtures and builders
# ---------------------------------------------------------------------------------------
def _wipe(engine) -> None:
    with engine.begin() as conn:
        for table in reversed(tables.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=pytest.mark.postgres)])
def db_engine(request, tmp_path):
    if request.param == "sqlite":
        eng = create_db_engine(f"sqlite:///{(tmp_path / 'repo.db').as_posix()}")
        init_db(eng)
    else:
        eng = create_db_engine(os.environ["LAUNCH_TEST_POSTGRES_URL"])
        init_db(eng)
        _wipe(eng)
    yield eng
    if request.param == "postgres":
        _wipe(eng)
    eng.dispose()


@pytest.fixture
def repo(db_engine) -> Repository:  # overrides the conftest fixture: runs on both databases
    return Repository(db_engine)


@pytest.fixture
def clock(monkeypatch):
    """A manual clock for the repository's ``utcnow`` (created_at / updated_at stamps)."""
    state = {"now": T0}

    def now():
        return state["now"]

    def advance(seconds: float = 1.0):
        state["now"] = state["now"] + timedelta(seconds=seconds)
        return state["now"]

    monkeypatch.setattr(repository_module, "utcnow", now)
    return advance


def add_user(engine, user_id: str, email: str | None = None) -> str:
    with engine.begin() as conn:
        conn.execute(insert(tables.users).values(
            id=user_id, email=email or f"{user_id}@example.com", full_name=user_id, password_hash="x",
            email_verified_at=None, is_admin=False, created_at=T0, updated_at=T0,
        ))
    return user_id


def count(engine, table: str, **where) -> int:
    t = tables.metadata.tables[table]
    query = select(func.count()).select_from(t)
    for column, value in where.items():
        query = query.where(t.c[column] == value)
    with engine.connect() as conn:
        return conn.execute(query).scalar_one()


def two_founder_facts() -> CaseFacts:
    return CaseFacts(
        business_description="bookkeeping software for small bakeries",
        founders=[
            Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("66.67"),
                    vesting_months=48, cliff_months=12),
            Founder(id="f2", name="Bob Diaz", email="bob@example.com", equity_percent=Decimal("33.33")),
        ],
        entity_type=EntityType.LLC,
        state="WY",
        incorporation_date=date(2026, 12, 1),
        name_preferences=["short", "friendly"],
        company_name="Crumb Ledger LLC",
        website=WebsiteRequirements(pages=["Home", "About"], services=["Bookkeeping"], contact_email="hi@crumb.test"),
    )


def custom_state() -> CaseState:
    return CaseState(
        active_agent=AgentId.LAW,
        facts_locked=True,
        facts_locked_at=T0,
        pending_fact="state",
        notices_given=["default_vesting:f2"],
        name_candidates=[NameCandidate(
            name="Crumb Ledger", rationale="short",
            domains=[DomainCheck(domain="crumbledger.com", status=DomainStatus.AVAILABLE, source="fake",
                                 checked_at=T0, detail="ok")],
            state_check=None, trademark_search_url="https://tmsearch.uspto.gov/",
        )],
        chosen_domain="crumbledger.com",
        legal_issues=[LegalIssue(code="x", severity="info", message="note")],
    )


def make_signature(founder_id: str, version: int, content: str, *, user_id: str | None, minute: int = 0,
                   acted_by: str | None = None) -> Signature:
    return Signature(
        founder_id=founder_id, version=version, signed_at=T0 + timedelta(minutes=minute), user_id=user_id,
        typed_name={"f1": "Alice Chen", "f2": "Bob Diaz"}[founder_id], consent_version=ESIGN_CONSENT_VERSION,
        content_sha256=document_sha256(content), ip="203.0.113.7", user_agent="Mozilla/5.0 (test)",
        acted_by_user_id=acted_by,
    )


def make_document(case_id: str, *, kind=DocumentKind.IP_ASSIGNMENT, founder_id: str | None = "f1",
                  doc_id: str | None = None, content: str = "IP assignment v1") -> Document:
    return Document(
        id=doc_id or f"doc_{kind.value[:6]}_{founder_id or 'all'}",
        case_id=case_id, kind=kind, title=f"{kind.value} {founder_id}", founder_id=founder_id, version=1,
        content=content, status=DocumentStatus.AWAITING_SIGNATURES,
        required_signers=[founder_id] if founder_id else ["f1", "f2"], signatures=[],
        created_at=T0, updated_at=T0,
    )


def make_build(case_id: str, version: int, *, build_id: str | None = None) -> SiteBuild:
    content = SiteContent(
        company_name="Crumb Ledger LLC", tagline="Books for bakers",
        pages=[SitePage(slug="index", title="Home", nav_label="Home",
                        sections=[SiteSection(heading="Hello", body="We do books", items=["a", "b"])])],
        contact=SiteContact(email="hi@crumb.test"), founders=[SiteFounder(name="Alice Chen", bio="CEO")],
        footer_note="(c) 2026",
    )
    report = QaReport(
        passed=False, round=0, checked_at=T0,
        checks=[QaCheckResult(check=QaCheckId.PAGES_PRESENT, label="Pages", passed=False,
                              issues=[QaIssue(check=QaCheckId.PAGES_PRESENT, severity="error", page="about",
                                              message="missing about page")])],
    )
    return SiteBuild(
        id=build_id or f"site_v{version}", case_id=case_id, version=version, content=content,
        bundle=SiteBundle(files=[SiteFile(path="index.html", content="<h1>Crumb</h1>", content_type="text/html"),
                                 SiteFile(path="styles.css", content="h1{}", content_type="text/css")]),
        qa_reports=[report, report.model_copy(update={"passed": True, "round": 1})],
        qa_passed=True, fix_rounds=1, status=SiteBuildStatus.QA_PASSED, created_at=T0, updated_at=T0,
    )


# ---------------------------------------------------------------------------------------
# AC 4: cases
# ---------------------------------------------------------------------------------------
def test_case_with_two_founders_decimal_equity_users_and_custom_state_round_trips(repo, db_engine, clock):
    alice = add_user(db_engine, "usr_alice")
    payer = add_user(db_engine, "usr_payer")
    created = repo.create_case(created_by=alice, facts=two_founder_facts(), state=custom_state())
    assert created.created_by == alice and created.billing_user_id == alice
    assert created.created_at == created.updated_at == T0
    assert repo.get_case(created.id) == created

    repo.set_billing_user(created.id, payer)
    clock(5)
    record = repo.get_case(created.id)
    assert record.billing_user_id == payer and record.created_by == alice
    equity = [f.equity_percent for f in record.facts.founders]
    assert equity == [Decimal("66.67"), Decimal("33.33")] and all(isinstance(e, Decimal) for e in equity)
    assert [str(e) for e in equity] == ["66.67", "33.33"]
    assert record.facts == two_founder_facts() and record.state == custom_state()
    assert record.state != CaseState()

    changed = record.model_copy(update={"facts": record.facts.model_copy(update={"state": "DE"})})
    saved = repo.save_case(changed)
    assert saved.updated_at == T0 + timedelta(seconds=5) and saved.created_at == T0
    assert saved.facts.state == "DE" and saved.billing_user_id == payer
    assert repo.get_case(created.id) == saved


def test_create_case_defaults_without_a_user(repo):
    record = repo.create_case()
    assert record.facts == CaseFacts() and record.state == CaseState()
    assert record.created_by is None and record.billing_user_id is None
    assert record.id.startswith("case_") and record.created_at.tzinfo is not None


def test_list_cases_returns_only_the_given_ids_newest_first(repo, clock):
    first = repo.create_case()
    clock()
    second = repo.create_case()
    clock()
    third = repo.create_case()
    clock()
    other = repo.create_case()
    listed = repo.list_cases([first.id, third.id, second.id, first.id, "case_unknown"])
    assert [c.id for c in listed] == [third.id, second.id, first.id]
    assert other.id not in {c.id for c in listed}
    assert repo.list_cases([]) == []
    assert all(isinstance(c, CaseRecord) for c in listed)


def test_save_case_and_set_billing_user_reject_unknown_ids(repo, db_engine):
    record = repo.create_case()
    with pytest.raises(NotFoundError):
        repo.save_case(record.model_copy(update={"id": "case_missing"}))
    with pytest.raises(NotFoundError):
        repo.set_billing_user("case_missing", add_user(db_engine, "usr_x"))
    with pytest.raises(NotFoundError):
        repo.set_billing_user(record.id, "usr_missing")
    with pytest.raises(NotFoundError):
        repo.create_case(created_by="usr_missing")


# ---------------------------------------------------------------------------------------
# AC 5: messages
# ---------------------------------------------------------------------------------------
def test_messages_get_consecutive_seq_per_case_and_round_trip(repo, clock):
    a = repo.create_case()
    b = repo.create_case()
    first = repo.append_messages(a.id, [
        ChatMessage(role=MessageRole.FOUNDER, founder_id="f1", content="Hi, we're starting a bakery app"),
        agent_message(AgentId.MANAGER, "Welcome!", suggested_replies=[SuggestedReply(label="Go", text="Let's go")],
                      payload={"n": 1, "nested": {"k": ["v"]}}),
    ])
    other = repo.append_messages(b.id, [ChatMessage(role=MessageRole.SYSTEM, kind=MessageKind.NOTICE, content="x")])
    second = repo.append_messages(a.id, [handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover",
                                                         reason="documents")])
    assert [m.seq for m in first] == [1, 2] and [m.seq for m in second] == [3] and [m.seq for m in other] == [1]
    assert all(m.case_id == a.id and m.id.startswith("msg_") and m.created_at == T0 for m in first + second)
    stored = repo.list_messages(a.id)
    assert stored == first + second
    assert stored[1].payload == {"n": 1, "nested": {"k": ["v"]}}
    assert stored[1].suggested_replies == [SuggestedReply(label="Go", text="Let's go")]
    assert stored[2].kind == MessageKind.HANDOFF and stored[2].agent == AgentId.MANAGER
    assert repo.list_messages(b.id) == other
    assert [m.seq for m in repo.list_messages(a.id, after_seq=1)] == [2, 3]
    assert repo.list_messages(a.id, after_seq=3) == []
    assert [m.seq for m in repo.list_messages(a.id, limit=2)] == [1, 2]
    assert [m.seq for m in repo.list_messages(a.id, after_seq=1, limit=1)] == [2]
    assert repo.append_messages(a.id, []) == []


def test_message_with_a_given_created_at_keeps_it(repo):
    case = repo.create_case()
    seeded = ChatMessage(role=MessageRole.FOUNDER, content="old", created_at=T0 - timedelta(days=1),
                         id="ignored", seq=99, case_id="ignored")
    [stored] = repo.append_messages(case.id, [seeded])
    assert stored.created_at == T0 - timedelta(days=1)
    assert stored.seq == 1 and stored.case_id == case.id and stored.id != "ignored"


def test_concurrent_appends_keep_seq_gap_free(repo):
    case = repo.create_case()
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(5):
                repo.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content=f"{n}-{i}")])
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert [m.seq for m in repo.list_messages(case.id)] == list(range(1, 21))


def test_messages_for_unknown_case_raise_not_found(repo):
    with pytest.raises(NotFoundError):
        repo.append_messages("case_missing", [ChatMessage(role=MessageRole.FOUNDER, content="x")])
    with pytest.raises(NotFoundError):
        repo.list_messages("case_missing")


# ---------------------------------------------------------------------------------------
# AC 6: documents, versions and signature evidence
# ---------------------------------------------------------------------------------------
def test_document_versions_optimistic_check_and_signature_evidence(repo, db_engine):
    alice = add_user(db_engine, "usr_alice")
    demo = add_user(db_engine, "usr_demo")
    case = repo.create_case(created_by=alice, facts=two_founder_facts())
    doc = make_document(case.id, founder_id=None, kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY,
                        content="Operating agreement v1")
    inserted = repo.save_document(doc, expected_version=None, created_by="system")
    assert inserted == doc and repo.get_document(doc.id) == doc
    assert count(db_engine, "document_versions", document_id=doc.id) == 1

    sig1 = make_signature("f1", 1, doc.content, user_id=alice, minute=1)
    signed = doc.model_copy(update={"signatures": [sig1], "updated_at": T0 + timedelta(minutes=1)})
    stored = repo.save_document(signed, expected_version=1, created_by="f1")
    assert stored == signed and stored.signatures[0] == sig1
    got = repo.get_document(doc.id).signatures[0]
    evidence = {k: getattr(got, k) for k in ("typed_name", "consent_version", "content_sha256", "user_id", "ip",
                                              "user_agent", "acted_by_user_id", "signed_at", "version")}
    assert evidence == {
        "typed_name": "Alice Chen", "consent_version": ESIGN_CONSENT_VERSION,
        "content_sha256": document_sha256("Operating agreement v1"), "user_id": alice, "ip": "203.0.113.7",
        "user_agent": "Mozilla/5.0 (test)", "acted_by_user_id": None, "signed_at": T0 + timedelta(minutes=1),
        "version": 1,
    }
    assert count(db_engine, "document_versions", document_id=doc.id) == 1  # same version: no new row

    # a stale save is rejected and changes nothing
    with pytest.raises(StaleVersionError) as stale:
        repo.save_document(signed.model_copy(update={"title": "x"}), expected_version=0, created_by="f2")
    assert stale.value.details["current_version"] == 1
    with pytest.raises(StaleVersionError):
        repo.save_document(signed, expected_version=None, created_by="f2")
    assert repo.get_document(doc.id) == signed

    # v2 (an edit by f2, demo-acted): new version row, only v2 signatures come back
    v2_content = "Operating agreement v2"
    sig2 = make_signature("f2", 2, v2_content, user_id=None, minute=3, acted_by=demo)
    v2 = signed.model_copy(update={"version": 2, "content": v2_content, "signatures": [sig2],
                                   "updated_at": T0 + timedelta(minutes=3)})
    assert repo.save_document(v2, expected_version=1, created_by="f2") == v2
    current = repo.get_document(doc.id)
    assert current.version == 2 and current.signatures == [sig2]
    assert current.signatures[0].acted_by_user_id == demo and current.signatures[0].user_id is None
    with pytest.raises(StaleVersionError):
        repo.save_document(v2.model_copy(update={"version": 3, "signatures": []}), expected_version=1,
                           created_by="f1")
    with db_engine.connect() as conn:
        versions = conn.execute(select(tables.document_versions.c.version, tables.document_versions.c.content,
                                       tables.document_versions.c.created_by)
                                .where(tables.document_versions.c.document_id == doc.id)
                                .order_by(tables.document_versions.c.version)).all()
        history = conn.execute(select(tables.signatures.c.founder_id, tables.signatures.c.version)
                               .where(tables.signatures.c.document_id == doc.id)
                               .order_by(tables.signatures.c.version)).all()
    assert [tuple(v) for v in versions] == [(1, "Operating agreement v1", "system"),
                                           (2, "Operating agreement v2", "f2")]
    assert [tuple(h) for h in history] == [("f1", 1), ("f2", 2)]  # old signatures stay for history

    # both founders sign v2; executed; signatures come back in signing order
    sig1b = make_signature("f1", 2, v2_content, user_id=alice, minute=4)
    executed = v2.model_copy(update={"signatures": [sig2, sig1b], "status": DocumentStatus.EXECUTED})
    assert repo.save_document(executed, expected_version=2, created_by="f1") == executed
    assert repo.get_document(doc.id).status == DocumentStatus.EXECUTED


def test_save_document_rules(repo, db_engine):
    case = repo.create_case(facts=two_founder_facts())
    doc = make_document(case.id)
    repo.save_document(doc, expected_version=None, created_by="system")
    with pytest.raises(ConflictError):  # one document per (case, kind, founder)
        repo.save_document(doc.model_copy(update={"id": "doc_other"}), expected_version=None, created_by="system")

    # ... company-wide documents (no founder) included, which the UNIQUE constraint misses (NULLs)
    summary = make_document(case.id, kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY, founder_id=None)
    repo.save_document(summary, expected_version=None, created_by="system")
    with pytest.raises(ConflictError):
        repo.save_document(summary.model_copy(update={"id": "doc_summary_2"}), expected_version=None,
                           created_by="system")
    # an update cannot turn a document into a twin of another one either
    other_founder = make_document(case.id, founder_id="f2")
    repo.save_document(other_founder, expected_version=None, created_by="system")
    with pytest.raises(ConflictError):
        repo.save_document(other_founder.model_copy(update={"founder_id": "f1"}), expected_version=1,
                           created_by="system")
    with pytest.raises(ConflictError):
        repo.save_document(other_founder.model_copy(update={"kind": DocumentKind.OPERATING_AGREEMENT_SUMMARY,
                                                            "founder_id": None}),
                           expected_version=1, created_by="system")
    # the same kind for another company is fine
    elsewhere = repo.create_case(facts=two_founder_facts())
    repo.save_document(summary.model_copy(update={"id": "doc_summary_elsewhere", "case_id": elsewhere.id}),
                       expected_version=None, created_by="system")
    assert sorted((d.id, d.founder_id or "") for d in repo.list_documents(case.id)) == sorted([
        (doc.id, "f1"), (other_founder.id, "f2"), (summary.id, ""),
    ])
    assert [d.id for d in repo.list_documents(elsewhere.id)] == ["doc_summary_elsewhere"]
    assert repo.get_document(other_founder.id) == other_founder  # the rejected updates changed nothing
    with pytest.raises(NotFoundError):  # a document never moves to another company
        repo.save_document(doc.model_copy(update={"case_id": elsewhere.id}), expected_version=1, created_by="s")
    with pytest.raises(ValueError):  # a founder signs a version once
        sig = make_signature("f1", 1, doc.content, user_id=None)
        repo.save_document(doc.model_copy(update={"signatures": [sig, sig]}), expected_version=1, created_by="f1")

    with pytest.raises(NotFoundError):
        repo.save_document(make_document("case_missing", doc_id="doc_x"), expected_version=None, created_by="s")
    with pytest.raises(NotFoundError):  # signer user ids must exist
        bad = doc.model_copy(update={"signatures": [make_signature("f1", 1, doc.content, user_id="usr_nobody")]})
        repo.save_document(bad, expected_version=1, created_by="f1")
    with pytest.raises(ValueError):  # a signature must be for the version being saved
        bad = doc.model_copy(update={"signatures": [make_signature("f1", 7, doc.content, user_id=None)]})
        repo.save_document(bad, expected_version=1, created_by="f1")
    assert repo.get_document(doc.id) == doc
    with pytest.raises(NotFoundError):
        repo.get_document("doc_missing")


def test_concurrent_company_wide_inserts_store_exactly_one(repo):
    """A double submit of "generate documents": the case lock serialises the inserts, so only
    one company-wide document survives and the others get ConflictError."""
    case = repo.create_case(facts=two_founder_facts())
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def worker(n: int) -> None:
        summary = make_document(case.id, kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY, founder_id=None,
                                doc_id=f"doc_summary_{n}")
        barrier.wait()
        try:
            repo.save_document(summary, expected_version=None, created_by="system")
            outcomes.append("saved")
        except ConflictError:
            outcomes.append("conflict")
        except BaseException as exc:  # pragma: no cover - reported below
            outcomes.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["conflict", "conflict", "conflict", "saved"]
    assert len(repo.list_documents(case.id)) == 1


def test_concurrent_saves_of_one_version_give_one_winner_and_stale_errors(repo):
    case = repo.create_case(facts=two_founder_facts())
    doc = make_document(case.id)
    repo.save_document(doc, expected_version=None, created_by="system")
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def worker(n: int) -> None:
        v2 = doc.model_copy(update={"version": 2, "content": f"v2 by {n}"})
        barrier.wait()
        try:
            repo.save_document(v2, expected_version=1, created_by=f"f{n}")
            outcomes.append("saved")
        except StaleVersionError:
            outcomes.append("stale")
        except BaseException as exc:  # pragma: no cover - reported below
            outcomes.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["saved", "stale", "stale", "stale"]
    assert repo.get_document(doc.id).version == 2


def test_list_documents_orders_by_kind_then_founder_order(repo):
    facts = two_founder_facts()
    facts = facts.model_copy(update={"founders": list(reversed(facts.founders))})  # f2 is the first founder
    case = repo.create_case(facts=facts)
    docs = [
        make_document(case.id, kind=DocumentKind.ELECTION_83B, founder_id="f1"),
        make_document(case.id, kind=DocumentKind.IP_ASSIGNMENT, founder_id="f1"),
        make_document(case.id, kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY, founder_id=None),
        make_document(case.id, kind=DocumentKind.IP_ASSIGNMENT, founder_id="f2"),
        make_document(case.id, kind=DocumentKind.ELECTION_83B, founder_id="f2"),
    ]
    for d in docs:
        repo.save_document(d, expected_version=None, created_by="system")
    listed = repo.list_documents(case.id)
    assert [(d.kind, d.founder_id) for d in listed] == [
        (DocumentKind.IP_ASSIGNMENT, "f2"), (DocumentKind.IP_ASSIGNMENT, "f1"),
        (DocumentKind.OPERATING_AGREEMENT_SUMMARY, None),
        (DocumentKind.ELECTION_83B, "f2"), (DocumentKind.ELECTION_83B, "f1"),
    ]
    assert repo.list_documents(repo.create_case().id) == []
    with pytest.raises(NotFoundError):
        repo.list_documents("case_missing")


# ---------------------------------------------------------------------------------------
# AC 7: audit, delete_document, checklist, site builds
# ---------------------------------------------------------------------------------------
def test_audit_order_and_filtering_and_delete_document_keeps_audit(repo, db_engine):
    case = repo.create_case(facts=two_founder_facts())
    other = repo.create_case()
    doc = make_document(case.id)
    repo.save_document(doc, expected_version=None, created_by="system")
    signed = doc.model_copy(update={"signatures": [make_signature("f1", 1, doc.content, user_id=None)]})
    repo.save_document(signed, expected_version=1, created_by="f1")
    entries = repo.append_audit([
        AuditEntry(case_id=case.id, actor="system", action=AuditAction.FACTS_LOCKED, at=T0),
        AuditEntry(case_id=case.id, document_id=doc.id, actor="law", action=AuditAction.CREATED, to_version=1,
                   detail={"kind": "ip_assignment", "n": [1, 2]}, at=T0 + timedelta(seconds=1)),
        AuditEntry(case_id=case.id, document_id=doc.id, actor="f1", action=AuditAction.SIGNED, from_version=1,
                   to_version=1, at=T0 + timedelta(seconds=2)),
    ])
    repo.append_audit([AuditEntry(case_id=other.id, actor="system", action=AuditAction.NAME_CHOSEN, at=T0)])
    ids = [e.id for e in entries]
    assert all(isinstance(i, int) for i in ids) and ids == sorted(ids)
    assert repo.list_audit(case.id) == entries
    assert [e.action for e in repo.list_audit(case.id, document_id=doc.id)] == [AuditAction.CREATED,
                                                                               AuditAction.SIGNED]
    assert repo.list_audit(case.id)[1].detail == {"kind": "ip_assignment", "n": [1, 2]}
    assert [e.action for e in repo.list_audit(other.id)] == [AuditAction.NAME_CHOSEN]
    assert repo.append_audit([]) == []

    repo.delete_document(doc.id)
    with pytest.raises(NotFoundError):
        repo.get_document(doc.id)
    assert count(db_engine, "document_versions", document_id=doc.id) == 0
    assert count(db_engine, "signatures", document_id=doc.id) == 0
    assert repo.list_audit(case.id) == entries  # audit stays
    with pytest.raises(NotFoundError):
        repo.delete_document(doc.id)
    with pytest.raises(NotFoundError):
        repo.append_audit([AuditEntry(case_id="case_missing", actor="system", action=AuditAction.CREATED, at=T0)])
    with pytest.raises(NotFoundError):
        repo.list_audit("case_missing")


def test_checklist_upserts(repo):
    case = repo.create_case()
    assert repo.get_checklist(case.id) == {}
    repo.set_checklist_item(case.id, "file_articles", True, "f1")
    repo.set_checklist_item(case.id, "get_ein", True, None)
    repo.set_checklist_item(case.id, "file_articles", False, "f2")
    assert repo.get_checklist(case.id) == {"file_articles": False, "get_ein": True}
    repo.set_checklist_item(case.id, "file_articles", True, "f2")
    assert repo.get_checklist(case.id) == {"file_articles": True, "get_ein": True}
    with pytest.raises(NotFoundError):
        repo.set_checklist_item("case_missing", "x", True, None)
    with pytest.raises(NotFoundError):
        repo.get_checklist("case_missing")


def test_site_builds_round_trip_and_latest_picks_the_highest_version(repo):
    case = repo.create_case()
    assert repo.latest_site_build(case.id) is None and repo.list_site_builds(case.id) == []
    v1, v3, v2 = make_build(case.id, 1), make_build(case.id, 3), make_build(case.id, 2)
    for build in (v1, v3, v2):
        assert repo.save_site_build(build) == build
    got = repo.get_site_build(v1.id)
    assert got == v1 and got.bundle.get("index.html").content == "<h1>Crumb</h1>"
    assert got.qa_reports[0].checks[0].issues[0].message == "missing about page"
    assert repo.latest_site_build(case.id) == v3
    assert [b.version for b in repo.list_site_builds(case.id)] == [1, 2, 3]

    deployed = v3.model_copy(update={"status": SiteBuildStatus.DEPLOYED, "deploy_url": "https://crumb.example",
                                     "deploy_message": "live", "override_by": "f1",
                                     "updated_at": T0 + timedelta(hours=1)})
    assert repo.save_site_build(deployed) == deployed  # update by id
    assert repo.latest_site_build(case.id) == deployed and len(repo.list_site_builds(case.id)) == 3
    with pytest.raises(ConflictError):
        repo.save_site_build(make_build(case.id, 2, build_id="site_dup"))
    with pytest.raises(ConflictError):  # an update onto another build's version
        repo.save_site_build(v1.model_copy(update={"version": 3}))
    other = repo.create_case()
    with pytest.raises(NotFoundError):  # a build never moves to another company
        repo.save_site_build(v1.model_copy(update={"case_id": other.id}))
    assert repo.get_site_build(v1.id) == v1 and repo.list_site_builds(other.id) == []
    with pytest.raises(NotFoundError):
        repo.get_site_build("site_missing")
    with pytest.raises(NotFoundError):
        repo.save_site_build(make_build("case_missing", 1, build_id="site_x"))
    with pytest.raises(NotFoundError):
        repo.latest_site_build("case_missing")
    with pytest.raises(NotFoundError):
        repo.list_site_builds("case_missing")


# ---------------------------------------------------------------------------------------
# AC 8: delete_case cascades
# ---------------------------------------------------------------------------------------
def _fill_case(repo, case_id: str) -> None:
    repo.append_messages(case_id, [ChatMessage(role=MessageRole.FOUNDER, content="hi")])
    doc = make_document(case_id)
    repo.save_document(doc, expected_version=None, created_by="system")
    v2 = doc.model_copy(update={"version": 2, "content": "v2",
                                "signatures": [make_signature("f1", 2, "v2", user_id=None)]})
    repo.save_document(v2, expected_version=1, created_by="f1")
    repo.append_audit([AuditEntry(case_id=case_id, document_id=doc.id, actor="f1", action=AuditAction.EDITED,
                                  at=T0)])
    repo.set_checklist_item(case_id, "get_ein", True, "f1")
    repo.save_site_build(make_build(case_id, 1, build_id=f"site_{case_id}"))


def test_delete_case_removes_every_case_owned_row(repo, db_engine):
    user = add_user(db_engine, "usr_owner")
    doomed = repo.create_case(created_by=user, facts=two_founder_facts())
    kept = repo.create_case(created_by=user, facts=two_founder_facts())
    _fill_case(repo, doomed.id)
    # a second company of the same user must be untouched
    repo.append_messages(kept.id, [ChatMessage(role=MessageRole.FOUNDER, content="keep me")])
    repo.set_checklist_item(kept.id, "get_ein", True, None)
    with db_engine.begin() as conn:  # a membership row (T-027's table) cascades too
        conn.execute(insert(tables.memberships).values(case_id=doomed.id, user_id=user, role="owner",
                                                      founder_id="f1", joined_at=T0))
    assert count(db_engine, "signatures") == 1 and count(db_engine, "document_versions") == 2

    repo.delete_case(doomed.id)
    with pytest.raises(NotFoundError):
        repo.get_case(doomed.id)
    for table in CASE_OWNED_TABLES:
        column = "document_id" if table in ("document_versions", "signatures") else "case_id"
        value = "doc_ip_ass_f1" if column == "document_id" else doomed.id
        assert count(db_engine, table, **{column: value}) == 0, table
    assert count(db_engine, "signatures") == 0 and count(db_engine, "document_versions") == 0
    assert count(db_engine, "memberships") == 0
    assert count(db_engine, "users") == 1  # the user outlives the company
    assert [m.content for m in repo.list_messages(kept.id)] == ["keep me"]
    assert repo.get_checklist(kept.id) == {"get_ein": True}
    with pytest.raises(NotFoundError):
        repo.delete_case(doomed.id)


def test_foreign_keys_are_enforced(db_engine):
    with pytest.raises(IntegrityError):
        with db_engine.begin() as conn:
            conn.execute(insert(tables.checklist_items).values(case_id="case_missing", item_id="x", done=True,
                                                              updated_by=None, updated_at=T0))


# ---------------------------------------------------------------------------------------
# AC 9: transactions, unknown ids, durability, no ORM rows
# ---------------------------------------------------------------------------------------
def test_transaction_rolls_back_everything_when_the_block_raises(repo, db_engine):
    case = repo.create_case()

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with repo.transaction() as tx:
            assert tx is repo
            tx.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="lost")])
            tx.set_checklist_item(case.id, "get_ein", True, None)
            new_case = repo.create_case()  # the same repository joins the open transaction
            with repo.transaction() as inner:  # nested: joins the outer one
                inner.append_audit([AuditEntry(case_id=case.id, actor="system", action=AuditAction.CREATED,
                                               at=T0)])
            assert len(tx.list_messages(case.id)) == 1  # visible inside the transaction
            raise Boom()
    assert repo.list_messages(case.id) == [] and repo.get_checklist(case.id) == {}
    assert repo.list_audit(case.id) == []
    with pytest.raises(NotFoundError):
        repo.get_case(new_case.id)
    assert count(db_engine, "cases") == 1


def test_transaction_commits_and_a_domain_error_inside_rolls_back(repo):
    case = repo.create_case()
    with repo.transaction() as tx:
        tx.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="kept")])
        tx.set_checklist_item(case.id, "get_ein", True, None)
    assert [m.content for m in repo.list_messages(case.id)] == ["kept"]
    with pytest.raises(NotFoundError):
        with repo.transaction() as tx:
            tx.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="lost")])
            tx.get_document("doc_missing")
    assert [m.content for m in repo.list_messages(case.id)] == ["kept"]


def test_a_caught_conflict_inside_a_transaction_leaves_it_usable(repo):
    """PostgreSQL aborts a transaction on a failed statement; the repository uses a savepoint
    there, so a handled ConflictError behaves the same on both databases."""
    case = repo.create_case(facts=two_founder_facts())
    doc = make_document(case.id)
    summary = make_document(case.id, kind=DocumentKind.OPERATING_AGREEMENT_SUMMARY, founder_id=None)
    with repo.transaction() as tx:
        tx.save_site_build(make_build(case.id, 1))  # the first write of the transaction
        with pytest.raises(ConflictError):  # unique (case, version) violated in the database
            tx.save_site_build(make_build(case.id, 1, build_id="site_dup"))
        tx.save_document(doc, expected_version=None, created_by="system")
        with pytest.raises(ConflictError):  # a duplicate document, caught by the explicit check
            tx.save_document(doc.model_copy(update={"id": "doc_dup"}), expected_version=None, created_by="s")
        tx.save_document(summary, expected_version=None, created_by="system")
        with pytest.raises(ConflictError):  # a duplicate company-wide document
            tx.save_document(summary.model_copy(update={"id": "doc_dup_all"}), expected_version=None,
                             created_by="s")
        tx.save_site_build(make_build(case.id, 9))
        with pytest.raises(ConflictError):  # an update onto another build's version (database constraint)
            tx.save_site_build(make_build(case.id, 1, build_id="site_v9"))
        # the transaction is still usable: more writes, then commit
        tx.set_checklist_item(case.id, "get_ein", True, None)
        tx.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="after the conflicts")])
        tx.save_site_build(make_build(case.id, 2))
    assert repo.get_checklist(case.id) == {"get_ein": True}
    assert [m.content for m in repo.list_messages(case.id)] == ["after the conflicts"]
    assert [b.id for b in repo.list_site_builds(case.id)] == ["site_v1", "site_v2", "site_v9"]
    assert sorted(d.id for d in repo.list_documents(case.id)) == sorted([doc.id, summary.id])


def test_unknown_ids_raise_not_found(repo):
    for call in (
        lambda: repo.get_case("case_missing"),
        lambda: repo.delete_case("case_missing"),
        lambda: repo.get_document("doc_missing"),
        lambda: repo.delete_document("doc_missing"),
        lambda: repo.get_site_build("site_missing"),
        lambda: repo.list_messages("case_missing"),
    ):
        with pytest.raises(NotFoundError) as exc:
            call()
        assert exc.value.http_status == 404 and exc.value.message


def test_data_survives_a_new_repository_and_engine_on_the_same_file(tmp_path):
    url = f"sqlite:///{(tmp_path / 'durable.db').as_posix()}"
    first = create_db_engine(url)
    init_db(first)
    add_user(first, "usr_alice")
    repo = Repository(first)
    case = repo.create_case(created_by="usr_alice", facts=two_founder_facts(), state=custom_state())
    msgs = repo.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="hello")])
    doc = repo.save_document(make_document(case.id), expected_version=None, created_by="system")
    build = repo.save_site_build(make_build(case.id, 1))
    repo.set_checklist_item(case.id, "get_ein", True, "f1")
    first.dispose()

    second = create_db_engine(url)
    try:
        init_db(second)  # idempotent on a migrated file: nothing is lost
        again = Repository(second)
        assert again.get_case(case.id) == case
        assert again.list_messages(case.id) == msgs
        assert again.get_document(doc.id) == doc
        assert again.get_site_build(build.id) == build
        assert again.get_checklist(case.id) == {"get_ein": True}
    finally:
        second.dispose()


def test_orm_rows_never_escape(repo, db_engine):
    add_user(db_engine, "usr_alice")
    case = repo.create_case(created_by="usr_alice", facts=two_founder_facts())
    doc = make_document(case.id)
    results = [
        case, repo.get_case(case.id), repo.list_cases([case.id]),
        repo.append_messages(case.id, [ChatMessage(role=MessageRole.FOUNDER, content="x")]),
        repo.list_messages(case.id), repo.save_document(doc, expected_version=None, created_by="s"),
        repo.get_document(doc.id), repo.list_documents(case.id),
        repo.append_audit([AuditEntry(case_id=case.id, actor="s", action=AuditAction.CREATED, at=T0)]),
        repo.list_audit(case.id), repo.save_site_build(make_build(case.id, 1)), repo.get_site_build("site_v1"),
        repo.latest_site_build(case.id), repo.list_site_builds(case.id),
    ]

    def check(value):
        if isinstance(value, list):
            for v in value:
                check(v)
        else:
            assert isinstance(value, BaseModel), type(value)

    for value in results:
        check(value)
    checklist = repo.get_checklist(case.id)
    assert type(checklist) is dict
    assert repo.set_checklist_item(case.id, "a", True, None) is None
    assert repo.set_billing_user(case.id, "usr_alice") is None
    with db_engine.connect() as conn:  # sanity: the raw table really holds JSON text
        facts_json = conn.execute(select(tables.cases.c.facts_json)).scalar_one()
    assert '"66.67"' in facts_json
