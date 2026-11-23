"""The case ``Repository`` (ADR-0012 methods as changed by ADR-0027). Owned by T-005.

SQLAlchemy Core on the tables of ``tables.py``; only pydantic domain objects cross this
boundary. Nested state is JSON text (``model_dump_json``), so ``Decimal`` equity survives as
its exact decimal string. Timestamps are stored as UTC and always read back timezone-aware.

Every public method runs in its own transaction. ``transaction()`` binds this repository to
one connection for the current thread / task: every call made through it (or through the
yielded object, which is the same repository) inside the block commits or rolls back
together. Other threads using the same repository are unaffected.

Unknown ids raise ``NotFoundError``. ``list_cases`` is the one exception: it returns the
companies that exist among the ids it is given.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Sequence

from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.engine import Connection, Engine, Row
from sqlalchemy.exc import IntegrityError

from ..domain.documents import AuditAction, AuditEntry, Document, DocumentKind, DocumentStatus, Signature
from ..domain.errors import ConflictError, NotFoundError, StaleVersionError
from ..domain.helpers import new_id, utcnow
from ..domain.messages import AgentId, ChatMessage, MessageKind, MessageRole, SuggestedReply
from ..domain.state import CaseRecord, CaseState
from ..domain.types import CaseFacts
from ..domain.website import QaReport, SiteBuild, SiteBuildStatus, SiteBundle, SiteContent, SiteFile
from .tables import (
    audit_log,
    cases,
    checklist_items,
    document_versions,
    documents,
    messages as message_rows,
    signatures,
    site_builds,
    users,
)

__all__ = ["Repository"]

_KIND_ORDER = {kind: i for i, kind in enumerate(DocumentKind)}


# ---------------------------------------------------------------------------------------
# value conversion
# ---------------------------------------------------------------------------------------
def _to_db(dt: datetime) -> datetime:
    """Aware UTC for storage (a naive value is taken to be UTC already)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _from_db(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive UTC, PostgreSQL an aware value in the session zone: both -> aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _case_from_row(row: Row) -> CaseRecord:
    return CaseRecord(
        id=row.id,
        created_at=_from_db(row.created_at),
        updated_at=_from_db(row.updated_at),
        facts=CaseFacts.model_validate_json(row.facts_json),
        state=CaseState.model_validate_json(row.state_json),
        created_by=row.created_by,
        billing_user_id=row.billing_user_id,
    )


def _message_from_row(row: Row) -> ChatMessage:
    return ChatMessage(
        id=row.id,
        case_id=row.case_id,
        seq=row.seq,
        role=MessageRole(row.role),
        agent=AgentId(row.agent) if row.agent is not None else None,
        founder_id=row.founder_id,
        kind=MessageKind(row.kind),
        content=row.content,
        payload=json.loads(row.payload_json),
        suggested_replies=[SuggestedReply.model_validate(r) for r in json.loads(row.suggested_json)],
        created_at=_from_db(row.created_at),
    )


def _signature_from_row(row: Row) -> Signature:
    return Signature(
        founder_id=row.founder_id,
        version=row.version,
        signed_at=_from_db(row.signed_at),
        user_id=row.user_id,
        typed_name=row.typed_name,
        consent_version=row.consent_version,
        content_sha256=row.content_sha256,
        ip=row.ip,
        user_agent=row.user_agent,
        acted_by_user_id=row.acted_by_user_id,
    )


def _document_from_row(row: Row, sigs: list[Signature]) -> Document:
    return Document(
        id=row.id,
        case_id=row.case_id,
        kind=DocumentKind(row.kind),
        title=row.title,
        founder_id=row.founder_id,
        version=row.version,
        content=row.content,
        status=DocumentStatus(row.status),
        required_signers=json.loads(row.required_signers_json),
        signatures=sigs,
        created_at=_from_db(row.created_at),
        updated_at=_from_db(row.updated_at),
    )


def _audit_from_row(row: Row) -> AuditEntry:
    return AuditEntry(
        id=row.id,
        case_id=row.case_id,
        document_id=row.document_id,
        actor=row.actor,
        action=AuditAction(row.action),
        from_version=row.from_version,
        to_version=row.to_version,
        detail=json.loads(row.detail_json),
        at=_from_db(row.at),
    )


def _build_values(build: SiteBuild) -> dict[str, Any]:
    return {
        "case_id": build.case_id,
        "version": build.version,
        "content_json": build.content.model_dump_json(),
        "files_json": _dumps([f.model_dump(mode="json") for f in build.bundle.files]),
        "qa_reports_json": _dumps([r.model_dump(mode="json") for r in build.qa_reports]),
        "qa_passed": build.qa_passed,
        "fix_rounds": build.fix_rounds,
        "status": build.status.value,
        "deploy_url": build.deploy_url,
        "deploy_message": build.deploy_message,
        "override_by": build.override_by,
        "created_at": _to_db(build.created_at),
        "updated_at": _to_db(build.updated_at),
    }


def _build_from_row(row: Row) -> SiteBuild:
    return SiteBuild(
        id=row.id,
        case_id=row.case_id,
        version=row.version,
        content=SiteContent.model_validate_json(row.content_json),
        bundle=SiteBundle(files=[SiteFile.model_validate(f) for f in json.loads(row.files_json)]),
        qa_reports=[QaReport.model_validate(r) for r in json.loads(row.qa_reports_json)],
        qa_passed=row.qa_passed,
        fix_rounds=row.fix_rounds,
        status=SiteBuildStatus(row.status),
        deploy_url=row.deploy_url,
        deploy_message=row.deploy_message,
        override_by=row.override_by,
        created_at=_from_db(row.created_at),
        updated_at=_from_db(row.updated_at),
    )


class Repository:
    """Companies, chat, documents with signatures, audit, checklist and site builds."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        # The connection of an open ``transaction()`` for the current thread / task.
        self._bound: ContextVar[Connection | None] = ContextVar(f"repository_tx_{id(self)}", default=None)

    # ------------------------------------------------------------------------------------
    # transactions
    # ------------------------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator["Repository"]:
        """The same repository bound to one session: everything inside commits or rolls back together.

        Re-entering inside an open transaction joins it (the outermost block decides)."""
        if self._bound.get() is not None:
            yield self
            return
        with self.engine.begin() as connection:
            token = self._bound.set(connection)
            try:
                yield self
            finally:
                self._bound.reset(token)

    @contextmanager
    def _tx(self) -> Iterator[Connection]:
        bound = self._bound.get()
        if bound is not None:
            yield bound
            return
        with self.engine.begin() as connection:
            yield connection

    # ------------------------------------------------------------------------------------
    # existence checks
    # ------------------------------------------------------------------------------------
    @staticmethod
    def _require_case(conn: Connection, case_id: str) -> None:
        if conn.execute(select(cases.c.id).where(cases.c.id == case_id)).first() is None:
            raise NotFoundError("We couldn't find that company.", details={"case_id": case_id})

    @staticmethod
    def _require_users(conn: Connection, user_ids: Iterable[str | None]) -> None:
        wanted = {u for u in user_ids if u is not None}
        if not wanted:
            return
        found = set(conn.execute(select(users.c.id).where(users.c.id.in_(wanted))).scalars())
        missing = sorted(wanted - found)
        if missing:
            raise NotFoundError("We couldn't find that user.", details={"user_ids": missing})

    @staticmethod
    def _lock_case(conn: Connection, case_id: str) -> None:
        """Takes the write lock on the company row (PostgreSQL row lock, SQLite write lock) so
        concurrent appends to one case serialise; ``NotFoundError`` for an unknown id."""
        result = conn.execute(update(cases).where(cases.c.id == case_id).values(id=cases.c.id))
        if result.rowcount == 0:
            raise NotFoundError("We couldn't find that company.", details={"case_id": case_id})

    # ------------------------------------------------------------------------------------
    # cases
    # ------------------------------------------------------------------------------------
    def create_case(
        self, *, created_by: str | None = None, facts: CaseFacts | None = None, state: CaseState | None = None
    ) -> CaseRecord:
        """New company; ``billing_user_id = created_by``."""
        now = utcnow()
        record = CaseRecord(
            id=new_id("case"),
            created_at=now,
            updated_at=now,
            facts=facts if facts is not None else CaseFacts(),
            state=state if state is not None else CaseState(),
            created_by=created_by,
            billing_user_id=created_by,
        )
        with self._tx() as conn:
            self._require_users(conn, [created_by])
            conn.execute(insert(cases).values(
                id=record.id,
                created_at=_to_db(record.created_at),
                updated_at=_to_db(record.updated_at),
                facts_json=record.facts.model_dump_json(),
                state_json=record.state.model_dump_json(),
                created_by=record.created_by,
                billing_user_id=record.billing_user_id,
            ))
            return self._get_case(conn, record.id)

    @staticmethod
    def _get_case(conn: Connection, case_id: str) -> CaseRecord:
        row = conn.execute(select(cases).where(cases.c.id == case_id)).first()
        if row is None:
            raise NotFoundError("We couldn't find that company.", details={"case_id": case_id})
        return _case_from_row(row)

    def get_case(self, case_id: str) -> CaseRecord:
        """``NotFoundError`` for an unknown id."""
        with self._tx() as conn:
            return self._get_case(conn, case_id)

    def list_cases(self, case_ids: Sequence[str]) -> list[CaseRecord]:
        """Only these companies (the user's member case ids), newest first."""
        wanted = list(dict.fromkeys(case_ids))
        if not wanted:
            return []
        with self._tx() as conn:
            rows = conn.execute(
                select(cases).where(cases.c.id.in_(wanted)).order_by(cases.c.created_at.desc(), cases.c.id.desc())
            ).all()
            return [_case_from_row(r) for r in rows]

    def save_case(self, case: CaseRecord) -> CaseRecord:
        """Store facts and state; bumps ``updated_at``."""
        with self._tx() as conn:
            result = conn.execute(
                update(cases).where(cases.c.id == case.id).values(
                    facts_json=case.facts.model_dump_json(),
                    state_json=case.state.model_dump_json(),
                    updated_at=_to_db(utcnow()),
                )
            )
            if result.rowcount == 0:
                raise NotFoundError("We couldn't find that company.", details={"case_id": case.id})
            return self._get_case(conn, case.id)

    def set_billing_user(self, case_id: str, user_id: str) -> None:
        """Whose plan the company uses (ADR-0030). ``NotFoundError`` for an unknown case or user."""
        with self._tx() as conn:
            self._require_users(conn, [user_id])
            result = conn.execute(update(cases).where(cases.c.id == case_id).values(billing_user_id=user_id))
            if result.rowcount == 0:
                raise NotFoundError("We couldn't find that company.", details={"case_id": case_id})

    def delete_case(self, case_id: str) -> None:
        """Deletes the company and every case-owned row (cascade)."""
        with self._tx() as conn:
            result = conn.execute(delete(cases).where(cases.c.id == case_id))
            if result.rowcount == 0:
                raise NotFoundError("We couldn't find that company.", details={"case_id": case_id})

    # ------------------------------------------------------------------------------------
    # messages
    # ------------------------------------------------------------------------------------
    def append_messages(self, case_id: str, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        """Assigns id, case_id, seq (max+1...) and created_at; returns the stored copies in order.

        A message that already carries ``created_at`` keeps it (seeded history); the rest get now.
        Appends to one company are serialised, so ``seq`` stays gap-free under concurrency."""
        if not messages:
            with self._tx() as conn:
                self._require_case(conn, case_id)
            return []
        now = utcnow()
        with self._tx() as conn:
            self._lock_case(conn, case_id)
            last = conn.execute(
                select(func.max(message_rows.c.seq)).where(message_rows.c.case_id == case_id)
            ).scalar()
            seq = int(last or 0)
            rows: list[dict[str, Any]] = []
            for message in messages:
                seq += 1
                copy = message.model_copy(update={
                    "id": new_id("msg"),
                    "case_id": case_id,
                    "seq": seq,
                    "created_at": message.created_at if message.created_at is not None else now,
                })
                data = copy.model_dump(mode="json")
                rows.append({
                    "id": copy.id,
                    "case_id": case_id,
                    "seq": seq,
                    "role": copy.role.value,
                    "agent": copy.agent.value if copy.agent is not None else None,
                    "founder_id": copy.founder_id,
                    "kind": copy.kind.value,
                    "content": copy.content,
                    "payload_json": _dumps(data["payload"]),
                    "suggested_json": _dumps(data["suggested_replies"]),
                    "created_at": _to_db(copy.created_at),
                })
            conn.execute(insert(message_rows), rows)
            ids = [r["id"] for r in rows]
            fetched = {
                r.id: _message_from_row(r)
                for r in conn.execute(select(message_rows).where(message_rows.c.id.in_(ids))).all()
            }
            return [fetched[i] for i in ids]

    def list_messages(self, case_id: str, after_seq: int | None = None, limit: int | None = None) -> list[ChatMessage]:
        """Oldest first; ``after_seq`` keeps ``seq > after_seq``; ``limit`` caps the count."""
        with self._tx() as conn:
            self._require_case(conn, case_id)
            query = select(message_rows).where(message_rows.c.case_id == case_id)
            if after_seq is not None:
                query = query.where(message_rows.c.seq > after_seq)
            query = query.order_by(message_rows.c.seq)
            if limit is not None:
                query = query.limit(max(int(limit), 0))
            return [_message_from_row(r) for r in conn.execute(query).all()]

    # ------------------------------------------------------------------------------------
    # documents and sign-off
    # ------------------------------------------------------------------------------------
    def save_document(self, doc: Document, *, expected_version: int | None, created_by: str) -> Document:
        """Insert when new; else the stored version must equal ``expected_version``
        (``StaleVersionError``); writes ``document_versions`` for a new version; replaces the
        current version's signatures, with every evidence field."""
        for sig in doc.signatures:
            if sig.version != doc.version:
                raise ValueError(
                    f"signature of {sig.founder_id} is for version {sig.version}, document is at {doc.version}"
                )
        now_values = {
            "kind": doc.kind.value,
            "founder_id": doc.founder_id,
            "title": doc.title,
            "version": doc.version,
            "content": doc.content,
            "status": doc.status.value,
            "required_signers_json": _dumps(list(doc.required_signers)),
            "updated_at": _to_db(doc.updated_at),
        }
        with self._tx() as conn:
            stored = conn.execute(
                select(documents.c.case_id, documents.c.version).where(documents.c.id == doc.id)
            ).first()
            self._require_users(
                conn, [u for s in doc.signatures for u in (s.user_id, s.acted_by_user_id)]
            )
            if stored is None:
                self._require_case(conn, doc.case_id)
                try:
                    conn.execute(insert(documents).values(
                        id=doc.id, case_id=doc.case_id, created_at=_to_db(doc.created_at), **now_values
                    ))
                except IntegrityError as exc:
                    raise ConflictError(
                        "That document already exists for this company.",
                        details={"case_id": doc.case_id, "kind": doc.kind.value, "founder_id": doc.founder_id},
                    ) from exc
            else:
                if expected_version is None or stored.version != expected_version:
                    raise StaleVersionError(
                        "This document changed while you were looking at it. Reload it and try again.",
                        details={"document_id": doc.id, "current_version": stored.version,
                                 "expected_version": expected_version},
                    )
                result = conn.execute(
                    update(documents)
                    .where(and_(documents.c.id == doc.id, documents.c.version == expected_version))
                    .values(**now_values)
                )
                if result.rowcount == 0:  # someone else saved in between
                    current = conn.execute(select(documents.c.version).where(documents.c.id == doc.id)).scalar()
                    raise StaleVersionError(
                        "This document changed while you were looking at it. Reload it and try again.",
                        details={"document_id": doc.id, "current_version": current,
                                 "expected_version": expected_version},
                    )
            has_version = conn.execute(
                select(document_versions.c.version).where(
                    and_(document_versions.c.document_id == doc.id, document_versions.c.version == doc.version)
                )
            ).first()
            if has_version is None:
                conn.execute(insert(document_versions).values(
                    document_id=doc.id, version=doc.version, content=doc.content,
                    created_by=created_by, created_at=_to_db(doc.updated_at),
                ))
            conn.execute(delete(signatures).where(
                and_(signatures.c.document_id == doc.id, signatures.c.version == doc.version)
            ))
            if doc.signatures:
                conn.execute(insert(signatures), [
                    {
                        "document_id": doc.id,
                        "founder_id": s.founder_id,
                        "version": s.version,
                        "signed_at": _to_db(s.signed_at),
                        "user_id": s.user_id,
                        "typed_name": s.typed_name,
                        "consent_version": s.consent_version,
                        "ip": s.ip,
                        "user_agent": s.user_agent,
                        "content_sha256": s.content_sha256,
                        "acted_by_user_id": s.acted_by_user_id,
                    }
                    for s in doc.signatures
                ])
            return self._get_document(conn, doc.id)

    @staticmethod
    def _current_signatures(conn: Connection, doc_rows: Sequence[Row]) -> dict[str, list[Signature]]:
        """Signatures of each document's current version, in signing order."""
        out: dict[str, list[Signature]] = {r.id: [] for r in doc_rows}
        if not doc_rows:
            return out
        current = {r.id: r.version for r in doc_rows}
        rows = conn.execute(
            select(signatures)
            .where(signatures.c.document_id.in_(list(current)))
            .order_by(signatures.c.signed_at, signatures.c.founder_id)
        ).all()
        for r in rows:
            if current[r.document_id] == r.version:
                out[r.document_id].append(_signature_from_row(r))
        return out

    def _get_document(self, conn: Connection, document_id: str) -> Document:
        row = conn.execute(select(documents).where(documents.c.id == document_id)).first()
        if row is None:
            raise NotFoundError("We couldn't find that document.", details={"document_id": document_id})
        return _document_from_row(row, self._current_signatures(conn, [row])[row.id])

    def get_document(self, document_id: str) -> Document:
        """``NotFoundError`` for an unknown id; signatures of the current version only."""
        with self._tx() as conn:
            return self._get_document(conn, document_id)

    def list_documents(self, case_id: str) -> list[Document]:
        """Stable order: kind, then founder order."""
        with self._tx() as conn:
            case = self._get_case(conn, case_id)
            rows = conn.execute(select(documents).where(documents.c.case_id == case_id)).all()
            founder_order = {f.id: i for i, f in enumerate(case.facts.founders)}

            def key(r: Row):
                kind = DocumentKind(r.kind)
                if r.founder_id is None:
                    founder = (-1, "")
                else:
                    founder = (founder_order.get(r.founder_id, len(founder_order)), r.founder_id)
                return (_KIND_ORDER[kind], founder, r.id)

            rows = sorted(rows, key=key)
            sigs = self._current_signatures(conn, rows)
            return [_document_from_row(r, sigs[r.id]) for r in rows]

    def delete_document(self, document_id: str) -> None:
        """Removes the document, its versions and signatures; audit stays."""
        with self._tx() as conn:
            conn.execute(delete(signatures).where(signatures.c.document_id == document_id))
            conn.execute(delete(document_versions).where(document_versions.c.document_id == document_id))
            result = conn.execute(delete(documents).where(documents.c.id == document_id))
            if result.rowcount == 0:
                raise NotFoundError("We couldn't find that document.", details={"document_id": document_id})

    def append_audit(self, entries: Sequence[AuditEntry]) -> list[AuditEntry]:
        """Stores the entries in order; returns copies with their assigned ids."""
        if not entries:
            return []
        stored: list[AuditEntry] = []
        with self._tx() as conn:
            for case_id in dict.fromkeys(e.case_id for e in entries):
                self._require_case(conn, case_id)
            for entry in entries:
                data = entry.model_dump(mode="json")
                result = conn.execute(insert(audit_log).values(
                    case_id=entry.case_id,
                    document_id=entry.document_id,
                    actor=entry.actor,
                    action=entry.action.value,
                    from_version=entry.from_version,
                    to_version=entry.to_version,
                    detail_json=_dumps(data["detail"]),
                    at=_to_db(entry.at),
                ))
                new_id_ = result.inserted_primary_key[0]
                row = conn.execute(select(audit_log).where(audit_log.c.id == new_id_)).one()
                stored.append(_audit_from_row(row))
        return stored

    def list_audit(self, case_id: str, document_id: str | None = None) -> list[AuditEntry]:
        """Oldest first."""
        with self._tx() as conn:
            self._require_case(conn, case_id)
            query = select(audit_log).where(audit_log.c.case_id == case_id)
            if document_id is not None:
                query = query.where(audit_log.c.document_id == document_id)
            return [_audit_from_row(r) for r in conn.execute(query.order_by(audit_log.c.id)).all()]

    # ------------------------------------------------------------------------------------
    # checklist
    # ------------------------------------------------------------------------------------
    def set_checklist_item(self, case_id: str, item_id: str, done: bool, updated_by: str | None) -> None:
        """Upsert one item's tick."""
        values = {"done": bool(done), "updated_by": updated_by, "updated_at": _to_db(utcnow())}
        with self._tx() as conn:
            self._require_case(conn, case_id)
            dialect = conn.dialect.name
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as upsert
            else:
                from sqlalchemy.dialects.sqlite import insert as upsert
            stmt = upsert(checklist_items).values(case_id=case_id, item_id=item_id, **values)
            stmt = stmt.on_conflict_do_update(index_elements=["case_id", "item_id"], set_=values)
            conn.execute(stmt)

    def get_checklist(self, case_id: str) -> dict[str, bool]:
        """``item_id -> done`` for every item ever ticked or unticked, by item id."""
        with self._tx() as conn:
            self._require_case(conn, case_id)
            rows = conn.execute(
                select(checklist_items.c.item_id, checklist_items.c.done)
                .where(checklist_items.c.case_id == case_id)
                .order_by(checklist_items.c.item_id)
            ).all()
            return {r.item_id: bool(r.done) for r in rows}

    # ------------------------------------------------------------------------------------
    # site builds
    # ------------------------------------------------------------------------------------
    def save_site_build(self, build: SiteBuild) -> SiteBuild:
        """Insert or update by id."""
        values = _build_values(build)
        with self._tx() as conn:
            self._require_case(conn, build.case_id)
            exists = conn.execute(select(site_builds.c.id).where(site_builds.c.id == build.id)).first()
            try:
                if exists is None:
                    conn.execute(insert(site_builds).values(id=build.id, **values))
                else:
                    conn.execute(update(site_builds).where(site_builds.c.id == build.id).values(**values))
            except IntegrityError as exc:
                raise ConflictError(
                    "That website version already exists for this company.",
                    details={"case_id": build.case_id, "version": build.version},
                ) from exc
            return self._get_site_build(conn, build.id)

    @staticmethod
    def _get_site_build(conn: Connection, build_id: str) -> SiteBuild:
        row = conn.execute(select(site_builds).where(site_builds.c.id == build_id)).first()
        if row is None:
            raise NotFoundError("We couldn't find that website build.", details={"build_id": build_id})
        return _build_from_row(row)

    def get_site_build(self, build_id: str) -> SiteBuild:
        with self._tx() as conn:
            return self._get_site_build(conn, build_id)

    def latest_site_build(self, case_id: str) -> SiteBuild | None:
        """The build with the highest version, or None before the first build."""
        with self._tx() as conn:
            self._require_case(conn, case_id)
            row = conn.execute(
                select(site_builds).where(site_builds.c.case_id == case_id)
                .order_by(site_builds.c.version.desc()).limit(1)
            ).first()
            return _build_from_row(row) if row is not None else None

    def list_site_builds(self, case_id: str) -> list[SiteBuild]:
        """Oldest version first."""
        with self._tx() as conn:
            self._require_case(conn, case_id)
            rows = conn.execute(
                select(site_builds).where(site_builds.c.case_id == case_id).order_by(site_builds.c.version)
            ).all()
            return [_build_from_row(r) for r in rows]
