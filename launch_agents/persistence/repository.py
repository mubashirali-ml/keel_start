"""The case ``Repository`` (ADR-0012 methods as changed by ADR-0027). Owned by T-005."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Sequence

from sqlalchemy.engine import Engine

from ..domain.documents import AuditEntry, Document
from ..domain.messages import ChatMessage
from ..domain.state import CaseRecord, CaseState
from ..domain.types import CaseFacts
from ..domain.website import SiteBuild

__all__ = ["Repository"]


class Repository:
    """Companies, chat, documents with signatures, audit, checklist and site builds."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @contextmanager
    def transaction(self) -> Iterator["Repository"]:
        """The same repository bound to one session: everything inside commits or rolls back together."""
        raise NotImplementedError("Repository.transaction is implemented in T-005")
        yield self  # pragma: no cover

    # cases
    def create_case(
        self, *, created_by: str | None = None, facts: CaseFacts | None = None, state: CaseState | None = None
    ) -> CaseRecord:
        """New company; ``billing_user_id = created_by``."""
        raise NotImplementedError("Repository.create_case is implemented in T-005")

    def get_case(self, case_id: str) -> CaseRecord:
        """``NotFoundError`` for an unknown id."""
        raise NotImplementedError("Repository.get_case is implemented in T-005")

    def list_cases(self, case_ids: Sequence[str]) -> list[CaseRecord]:
        """Only these companies (the user's member case ids), newest first."""
        raise NotImplementedError("Repository.list_cases is implemented in T-005")

    def save_case(self, case: CaseRecord) -> CaseRecord:
        """Store facts and state; bumps ``updated_at``."""
        raise NotImplementedError("Repository.save_case is implemented in T-005")

    def set_billing_user(self, case_id: str, user_id: str) -> None:
        raise NotImplementedError("Repository.set_billing_user is implemented in T-005")

    def delete_case(self, case_id: str) -> None:
        """Deletes the company and every case-owned row (cascade)."""
        raise NotImplementedError("Repository.delete_case is implemented in T-005")

    # messages
    def append_messages(self, case_id: str, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        """Assigns id, case_id, seq (max+1...) and created_at; returns the stored copies in order."""
        raise NotImplementedError("Repository.append_messages is implemented in T-005")

    def list_messages(self, case_id: str, after_seq: int | None = None, limit: int | None = None) -> list[ChatMessage]:
        raise NotImplementedError("Repository.list_messages is implemented in T-005")

    # documents and sign-off
    def save_document(self, doc: Document, *, expected_version: int | None, created_by: str) -> Document:
        """Insert when new; else the stored version must equal ``expected_version``
        (``StaleVersionError``); writes ``document_versions`` for a new version; replaces the
        current version's signatures, with every evidence field."""
        raise NotImplementedError("Repository.save_document is implemented in T-005")

    def get_document(self, document_id: str) -> Document:
        raise NotImplementedError("Repository.get_document is implemented in T-005")

    def list_documents(self, case_id: str) -> list[Document]:
        """Stable order: kind, then founder order."""
        raise NotImplementedError("Repository.list_documents is implemented in T-005")

    def delete_document(self, document_id: str) -> None:
        """Removes the document, its versions and signatures; audit stays."""
        raise NotImplementedError("Repository.delete_document is implemented in T-005")

    def append_audit(self, entries: Sequence[AuditEntry]) -> list[AuditEntry]:
        raise NotImplementedError("Repository.append_audit is implemented in T-005")

    def list_audit(self, case_id: str, document_id: str | None = None) -> list[AuditEntry]:
        """Oldest first."""
        raise NotImplementedError("Repository.list_audit is implemented in T-005")

    # checklist
    def set_checklist_item(self, case_id: str, item_id: str, done: bool, updated_by: str | None) -> None:
        raise NotImplementedError("Repository.set_checklist_item is implemented in T-005")

    def get_checklist(self, case_id: str) -> dict[str, bool]:
        raise NotImplementedError("Repository.get_checklist is implemented in T-005")

    # site builds
    def save_site_build(self, build: SiteBuild) -> SiteBuild:
        """Insert or update by id."""
        raise NotImplementedError("Repository.save_site_build is implemented in T-005")

    def get_site_build(self, build_id: str) -> SiteBuild:
        raise NotImplementedError("Repository.get_site_build is implemented in T-005")

    def latest_site_build(self, case_id: str) -> SiteBuild | None:
        raise NotImplementedError("Repository.latest_site_build is implemented in T-005")

    def list_site_builds(self, case_id: str) -> list[SiteBuild]:
        raise NotImplementedError("Repository.list_site_builds is implemented in T-005")
