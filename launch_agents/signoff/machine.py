"""Pure sign-off state machine (ADR-0014 rules with the ADR-0031 changes). Owned by T-004.

Every function returns a ``SignOffOutcome`` whose ``audit`` entries must be persisted, also
for rejections; the service then raises ``outcome.error``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from ..domain.documents import AuditEntry, Document, DraftDocument, SignatureEvidence
from ..domain.errors import LaunchError

__all__ = ["SignOffOutcome", "create_document", "edit", "is_legal_complete", "regenerate", "sign"]


class SignOffOutcome(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    document: Document  # unchanged when ok is False
    audit: list[AuditEntry]  # ALWAYS returned, also for rejections -> persist it
    invalidated: list[str] = []  # founder ids whose signatures were cancelled
    error: LaunchError | None = None  # StaleVersionError | NotASignerError | AlreadySignedError


def create_document(case_id: str, draft: DraftDocument, *, now: datetime) -> SignOffOutcome:
    """Version 1, awaiting signatures, ``CREATED`` audit (T-004)."""
    raise NotImplementedError("create_document is implemented in T-004")


def sign(doc: Document, founder_id: str, version: int, *, evidence: SignatureEvidence, now: datetime) -> SignOffOutcome:
    """Record a signature bound to ``evidence.content_sha256``; executes on the last one (T-004)."""
    raise NotImplementedError("sign is implemented in T-004")


def edit(
    doc: Document, editor_id: str, version: int, new_content: str, *, evidence: SignatureEvidence, now: datetime
) -> SignOffOutcome:
    """New version; other signatures cancelled; the editor signs the new content (T-004)."""
    raise NotImplementedError("edit is implemented in T-004")


def regenerate(doc: Document, draft: DraftDocument, *, now: datetime, actor: str = "system") -> SignOffOutcome:
    """Facts changed after drafting: new version, all signatures cancelled (T-004)."""
    raise NotImplementedError("regenerate is implemented in T-004")


def is_legal_complete(docs: Sequence[Document]) -> bool:
    """Non-empty and every document executed (T-004)."""
    raise NotImplementedError("is_legal_complete is implemented in T-004")
