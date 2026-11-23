"""T-005 feature run: the case Repository end to end, as a service would use it.

Creates a temp SQLite file, runs ``init_db`` (Alembic to head), prints the head and the
tables; stores a company created by a user, three chat messages, a document at v1 with one
e-signature (evidence printed), then v2 (a stale save is rejected), audit entries,
checklist ticks and a site build; opens a NEW engine on the same file and reads everything
back, asserting equality; deletes the company and prints the (empty) case-owned row counts.
Repeats the round trip on PostgreSQL when ``LAUNCH_TEST_POSTGRES_URL`` is set.

Exits non-zero on any failed assertion.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, inspect, insert, select

from launch_agents.domain.documents import AuditAction, AuditEntry, Document, DocumentKind, DocumentStatus, Signature
from launch_agents.domain.errors import StaleVersionError
from launch_agents.domain.helpers import document_sha256, new_id
from launch_agents.domain.messages import AgentId, ChatMessage, MessageRole, agent_message, handoff_message
from launch_agents.domain.state import CaseState
from launch_agents.domain.types import CaseFacts, EntityType, Founder
from launch_agents.domain.website import (
    QaCheckId,
    QaCheckResult,
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
from launch_agents.persistence import tables
from launch_agents.persistence.engine import create_db_engine, init_db, schema_is_current
from launch_agents.persistence.repository import Repository

T0 = datetime(2026, 11, 23, 10, 0, 0, tzinfo=timezone.utc)
CASE_OWNED = ("messages", "documents", "document_versions", "signatures", "audit_log", "checklist_items",
              "site_builds")


def show(label: str, value) -> None:
    print(f"  {label}: {value}")


def count_rows(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(tables.metadata.tables[table])).scalar_one()


def round_trip(make_engine, label: str) -> None:
    print(f"=== {label} ===")
    engine = make_engine()
    init_db(engine)
    init_db(engine)  # idempotent
    with engine.connect() as conn:
        from alembic.migration import MigrationContext

        head = MigrationContext.configure(conn).get_current_revision()
    names = sorted(set(inspect(engine).get_table_names()) - {"alembic_version"})
    show("migration head", head)
    show("schema_is_current", schema_is_current(engine))
    show(f"tables ({len(names)})", ", ".join(names))
    assert head == "0001_initial" and schema_is_current(engine) and names == sorted(tables.TABLE_NAMES)

    # a user (the accounts repository is another ticket: insert the row directly)
    user_id = new_id("usr")
    with engine.begin() as conn:
        conn.execute(insert(tables.users).values(
            id=user_id, email=f"{user_id}@example.com", full_name="Alice Chen", password_hash="(argon2)",
            email_verified_at=T0, is_admin=False, created_at=T0, updated_at=T0))
    repo = Repository(engine)

    facts = CaseFacts(
        business_description="bookkeeping software for small bakeries",
        founders=[Founder(id="f1", name="Alice Chen", email="alice@example.com", equity_percent=Decimal("62.5"),
                          vesting_months=48, cliff_months=12),
                  Founder(id="f2", name="Bob Diaz", email="bob@example.com", equity_percent=Decimal("37.5"))],
        entity_type=EntityType.LLC, state="WY", incorporation_date=date(2026, 12, 1),
        company_name="Crumb Ledger LLC",
    )
    case = repo.create_case(created_by=user_id, facts=facts, state=CaseState(active_agent=AgentId.LAW))
    print("company")
    show("id", case.id)
    show("created_by / billing_user_id", f"{case.created_by} / {case.billing_user_id}")
    show("equity", [str(f.equity_percent) for f in case.facts.founders])
    assert case.billing_user_id == user_id

    msgs = repo.append_messages(case.id, [
        ChatMessage(role=MessageRole.FOUNDER, founder_id="f1", content="We want to form a Wyoming LLC."),
        handoff_message(AgentId.MANAGER, AgentId.LAW, direction="handover", reason="founding documents"),
        agent_message(AgentId.LAW, "I drafted your IP assignment."),
    ])
    print("messages")
    for m in msgs:
        show(f"seq {m.seq}", f"[{m.role.value}/{m.agent.value if m.agent else m.founder_id}] {m.content}")
    assert [m.seq for m in msgs] == [1, 2, 3]

    v1_text = "IP assignment: Alice Chen assigns all company-related IP to Crumb Ledger LLC. (v1)"
    doc = Document(
        id=new_id("doc"), case_id=case.id, kind=DocumentKind.IP_ASSIGNMENT, title="IP assignment - Alice Chen",
        founder_id="f1", version=1, content=v1_text, status=DocumentStatus.AWAITING_SIGNATURES,
        required_signers=["f1"], signatures=[], created_at=T0, updated_at=T0,
    )
    repo.save_document(doc, expected_version=None, created_by="law")
    sig = Signature(founder_id="f1", version=1, signed_at=T0 + timedelta(minutes=5), user_id=user_id,
                    typed_name="Alice Chen", consent_version="esign-2026-11", content_sha256=document_sha256(v1_text),
                    ip="203.0.113.7", user_agent="Mozilla/5.0 (feature run)", acted_by_user_id=None)
    signed = repo.save_document(doc.model_copy(update={"signatures": [sig], "status": DocumentStatus.EXECUTED,
                                                       "updated_at": sig.signed_at}),
                                expected_version=1, created_by="f1")
    print("document v1 signed; evidence:")
    for key, value in signed.signatures[0].model_dump(mode="json").items():
        show(key, value)
    assert signed.signatures == [sig]

    v2_text = v1_text.replace("(v1)", "(v2, includes prior inventions schedule)")
    v2 = signed.model_copy(update={"version": 2, "content": v2_text, "signatures": [],
                                   "status": DocumentStatus.AWAITING_SIGNATURES,
                                   "updated_at": T0 + timedelta(minutes=9)})
    v2 = repo.save_document(v2, expected_version=1, created_by="f1")
    try:
        repo.save_document(v2.model_copy(update={"title": "stale"}), expected_version=1, created_by="f2")
    except StaleVersionError as exc:
        show("stale save (expected_version=1 while at v2)", f"rejected: {exc.code} {exc.details}")
    else:
        raise AssertionError("a stale save was accepted")
    show("document now", f"v{v2.version}, signatures on current version: {len(v2.signatures)}")
    assert v2.version == 2 and v2.signatures == []

    audit = repo.append_audit([
        AuditEntry(case_id=case.id, actor="system", action=AuditAction.FACTS_LOCKED, at=T0),
        AuditEntry(case_id=case.id, document_id=doc.id, actor="law", action=AuditAction.CREATED, to_version=1,
                   at=T0 + timedelta(minutes=1)),
        AuditEntry(case_id=case.id, document_id=doc.id, actor="f1", action=AuditAction.SIGNED, from_version=1,
                   to_version=1, detail={"typed_name": "Alice Chen"}, at=T0 + timedelta(minutes=5)),
        AuditEntry(case_id=case.id, document_id=doc.id, actor="f1", action=AuditAction.EDITED, from_version=1,
                   to_version=2, at=T0 + timedelta(minutes=9)),
    ])
    print("audit")
    for e in audit:
        show(f"#{e.id}", f"{e.action.value} by {e.actor} ({e.from_version}->{e.to_version})")

    repo.set_checklist_item(case.id, "file_articles", True, "f1")
    repo.set_checklist_item(case.id, "get_ein", True, "f2")
    repo.set_checklist_item(case.id, "get_ein", False, "f2")
    show("checklist", repo.get_checklist(case.id))

    build = SiteBuild(
        id=new_id("site"), case_id=case.id, version=1,
        content=SiteContent(company_name="Crumb Ledger LLC", tagline="Books for bakers",
                            pages=[SitePage(slug="index", title="Home", nav_label="Home",
                                            sections=[SiteSection(heading="Welcome", body="Bookkeeping for bakeries")])],
                            contact=SiteContact(email="hello@crumbledger.test"),
                            founders=[SiteFounder(name="Alice Chen", bio="Founder")]),
        bundle=SiteBundle(files=[SiteFile(path="index.html", content="<h1>Crumb Ledger LLC</h1>",
                                          content_type="text/html")]),
        qa_reports=[QaReport(passed=True, round=0, checked_at=T0, checks=[
            QaCheckResult(check=QaCheckId.PAGES_PRESENT, label="Pages present", passed=True, issues=[])])],
        qa_passed=True, fix_rounds=0, status=SiteBuildStatus.QA_PASSED, created_at=T0, updated_at=T0,
    )
    repo.save_site_build(build)
    show("site build", f"v{build.version} {build.status.value}, {len(build.bundle.files)} file(s)")

    expected = {
        "case": repo.get_case(case.id), "messages": msgs, "document": v2, "audit": audit,
        "checklist": {"file_articles": True, "get_ein": False}, "build": build,
    }
    engine.dispose()

    # --- a NEW engine and repository on the same database ---------------------------------
    engine = make_engine()
    again = Repository(engine)
    read = {
        "case": again.get_case(case.id), "messages": again.list_messages(case.id),
        "document": again.get_document(doc.id), "audit": again.list_audit(case.id),
        "checklist": again.get_checklist(case.id), "build": again.latest_site_build(case.id),
    }
    print("read back through a new engine")
    show("company", f"{read['case'].facts.company_name}, founders "
                    f"{[(f.id, str(f.equity_percent)) for f in read['case'].facts.founders]}, "
                    f"active agent {read['case'].state.active_agent.value}")
    show("messages", [m.seq for m in read["messages"]])
    show("document", f"v{read['document'].version} {read['document'].status.value}")
    show("audit", [e.action.value for e in read["audit"]])
    show("checklist", read["checklist"])
    show("site build", f"v{read['build'].version} files={[f.path for f in read['build'].bundle.files]}")
    for key in expected:
        assert read[key] == expected[key], key
    show("equal to what was stored", True)
    with engine.connect() as conn:
        v1_sig = conn.execute(select(tables.signatures.c.version, tables.signatures.c.typed_name)
                              .where(tables.signatures.c.document_id == doc.id)).all()
        versions = conn.execute(select(tables.document_versions.c.version)
                                .where(tables.document_versions.c.document_id == doc.id)
                                .order_by(tables.document_versions.c.version)).scalars().all()
    show("document_versions rows", versions)
    show("signature history rows (version, typed name)", [tuple(r) for r in v1_sig])
    assert versions == [1, 2] and [tuple(r) for r in v1_sig] == [(1, "Alice Chen")]

    again.delete_case(case.id)
    counts = {t: count_rows(engine, t) for t in CASE_OWNED}
    print("after delete_case")
    for t, n in counts.items():
        show(t, n)
    assert all(n == 0 for n in counts.values()), counts
    with engine.begin() as conn:  # leave a shared PostgreSQL database as we found it
        conn.execute(delete(tables.users).where(tables.users.c.id == user_id))
    engine.dispose()
    print(f"=== {label}: OK ===")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{(Path(tmp) / 'feature_run.db').as_posix()}"
        print("SQLite file: <tmp>/feature_run.db")
        round_trip(lambda: create_db_engine(url), "SQLite")
    pg_url = os.environ.get("LAUNCH_TEST_POSTGRES_URL")
    if pg_url:
        round_trip(lambda: create_db_engine(pg_url), "PostgreSQL")
    else:
        print("PostgreSQL part skipped: LAUNCH_TEST_POSTGRES_URL is not set")
    print("FEATURE RUN T-005: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
