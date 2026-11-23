"""``LegalService``: cap table, documents, e-signatures, signed downloads, audit
(ADR-0013, ADR-0014, ADR-0031, ADR-0032). Owned by T-015."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..domain.accounts import CaseAccess
from ..domain.cap_table import CapTable
from ..domain.documents import AuditEntry, Document
from ..domain.helpers import utcnow
from ..domain.views import DocumentsOutcome, EditOutcome, EditRequest, SignRequest
from ..persistence.accounts import AccountsRepository
from ..persistence.repository import Repository
from ..persistence.team import TeamRepository
from ..ports.notifications import Notifier

__all__ = ["LegalService"]


class LegalService:
    """Implements ``LegalServicePort``."""

    def __init__(
        self,
        repo: Repository,
        accounts: AccountsRepository,
        team: TeamRepository,
        notifier: Notifier,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.repo = repo
        self.accounts = accounts
        self.team = team
        self.notifier = notifier
        self.clock = clock

    def cap_table(self, access: CaseAccess) -> CapTable:
        raise NotImplementedError("LegalService.cap_table is implemented in T-015")

    def cap_table_csv(self, access: CaseAccess) -> str:
        raise NotImplementedError("LegalService.cap_table_csv is implemented in T-015")

    def cap_table_xlsx(self, access: CaseAccess) -> bytes:
        raise NotImplementedError("LegalService.cap_table_xlsx is implemented in T-015")

    def generate_documents(self, access: CaseAccess) -> DocumentsOutcome:
        raise NotImplementedError("LegalService.generate_documents is implemented in T-015")

    def regenerate_if_drafted(self, access: CaseAccess) -> DocumentsOutcome:
        raise NotImplementedError("LegalService.regenerate_if_drafted is implemented in T-015")

    def list_documents(self, access: CaseAccess) -> list[Document]:
        raise NotImplementedError("LegalService.list_documents is implemented in T-015")

    def get_document(self, access: CaseAccess, document_id: str) -> Document:
        raise NotImplementedError("LegalService.get_document is implemented in T-015")

    def sign(self, access: CaseAccess, document_id: str, req: SignRequest) -> Document:
        raise NotImplementedError("LegalService.sign is implemented in T-015")

    def edit(self, access: CaseAccess, document_id: str, req: EditRequest) -> EditOutcome:
        raise NotImplementedError("LegalService.edit is implemented in T-015")

    def signed_pdf(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]:
        raise NotImplementedError("LegalService.signed_pdf is implemented in T-015")

    def docx(self, access: CaseAccess, document_id: str) -> tuple[str, bytes]:
        raise NotImplementedError("LegalService.docx is implemented in T-015")

    def audit(self, access: CaseAccess) -> list[AuditEntry]:
        raise NotImplementedError("LegalService.audit is implemented in T-015")

    def legal_complete(self, access: CaseAccess) -> bool:
        raise NotImplementedError("LegalService.legal_complete is implemented in T-015")
