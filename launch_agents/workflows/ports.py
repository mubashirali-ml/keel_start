"""Service protocols used across workflows (ADR-0032). Implemented in T-001.

``LegalService`` (T-015) and ``WebsiteService`` (T-013) implement these; ``CaseService``
(T-014) depends only on the protocols, so the three are built in parallel.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.accounts import Actor, CaseAccess
from ..domain.cap_table import CapTable
from ..domain.documents import AuditEntry, Document
from ..domain.jobs import JobRecord
from ..domain.views import DocumentsOutcome, EditOutcome, EditRequest, SignRequest, SiteBuildOutcome
from ..domain.website import SiteBuild, SiteFile

__all__ = ["EditRequest", "LegalServicePort", "SignRequest", "WebsiteServicePort"]


@runtime_checkable
class LegalServicePort(Protocol):
    def cap_table(self, access: CaseAccess) -> CapTable: ...

    def cap_table_csv(self, access: CaseAccess) -> str: ...

    def cap_table_xlsx(self, access: CaseAccess) -> bytes: ...

    def generate_documents(self, access: CaseAccess) -> DocumentsOutcome:
        """Needs ``Feature.DOCUMENTS``; ``FactsNotReadyError`` unless the facts are locked."""
        ...

    def regenerate_if_drafted(self, access: CaseAccess) -> DocumentsOutcome:
        """Called by ``CaseService`` after the facts are re-locked; no documents -> no-op."""
        ...

    def list_documents(self, access: CaseAccess) -> list[Document]: ...

    def get_document(self, access: CaseAccess, document_id: str) -> Document:
        """``NotFoundError`` if the document is not in this company."""
        ...

    def sign(self, access: CaseAccess, document_id: str, req: SignRequest) -> Document: ...

    def edit(self, access: CaseAccess, document_id: str, req: EditRequest) -> EditOutcome: ...

    def signed_pdf(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]:
        """``(filename, bytes)``."""
        ...

    def docx(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]: ...

    def audit(self, access: CaseAccess) -> list[AuditEntry]: ...

    def legal_complete(self, access: CaseAccess) -> bool: ...


@runtime_checkable
class WebsiteServicePort(Protocol):
    def request_build(self, access: CaseAccess, change_request: str | None = None) -> JobRecord:
        """``NameNotChosenError`` without a company name."""
        ...

    def request_deploy(self, access: CaseAccess, *, override_qa: bool = False) -> JobRecord:
        """Needs ``Feature.WEBSITE_DEPLOY``."""
        ...

    def run_build(self, case_id: str, change_request: str | None, actor: Actor) -> SiteBuildOutcome:
        """The ``website.build`` job handler's work."""
        ...

    def run_deploy(self, case_id: str, actor: Actor, *, override_qa: bool) -> SiteBuildOutcome:
        """The ``website.deploy`` job handler's work."""
        ...

    def latest(self, access: CaseAccess) -> SiteBuild | None: ...

    def preview_file(self, access: CaseAccess, path: str) -> SiteFile: ...

    def download_zip(self, access: CaseAccess) -> bytes: ...
