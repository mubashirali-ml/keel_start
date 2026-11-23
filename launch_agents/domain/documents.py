"""Founding documents, e-signatures and the audit log (ADR-0014 as changed by ADR-0031)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

__all__ = [
    "AuditAction",
    "AuditEntry",
    "Document",
    "DocumentKind",
    "DocumentStatus",
    "DraftDocument",
    "Signature",
    "SignatureEvidence",
]


class DocumentKind(str, Enum):
    IP_ASSIGNMENT = "ip_assignment"
    BYLAWS_SUMMARY = "bylaws_summary"
    OPERATING_AGREEMENT_SUMMARY = "operating_agreement_summary"
    ELECTION_83B = "election_83b"


class DocumentStatus(str, Enum):
    AWAITING_SIGNATURES = "awaiting_signatures"
    EXECUTED = "executed"


class SignatureEvidence(BaseModel):
    """What the signer gives plus what the server observed (ADR-0031)."""

    user_id: str | None  # None only for system-seeded fixtures in tests
    typed_name: str
    consent_version: str
    content_sha256: str  # of the version being signed (for an edit: of the new content)
    ip: str | None = None
    user_agent: str | None = None
    acted_by_user_id: str | None = None  # demo mode only (ADR-0026)


class Signature(BaseModel):
    """A recorded e-signature on one document version (replaces the ADR-0014 shape)."""

    founder_id: str
    version: int
    signed_at: datetime
    user_id: str | None
    typed_name: str
    consent_version: str
    content_sha256: str
    ip: str | None = None
    user_agent: str | None = None
    acted_by_user_id: str | None = None


class DraftDocument(BaseModel):
    kind: DocumentKind
    title: str
    founder_id: str | None
    content: str
    required_signers: list[str]


class Document(BaseModel):
    id: str
    case_id: str
    kind: DocumentKind
    title: str
    founder_id: str | None
    version: int
    content: str
    status: DocumentStatus
    required_signers: list[str]
    signatures: list[Signature]  # current version only
    created_at: datetime
    updated_at: datetime


class AuditAction(str, Enum):
    CREATED = "created"
    SIGNED = "signed"
    EDITED = "edited"
    SIGNATURES_INVALIDATED = "signatures_invalidated"
    EXECUTED = "executed"
    REOPENED = "reopened"
    REGENERATED = "regenerated"
    REJECTED_STALE = "rejected_stale"
    REJECTED_NOT_SIGNER = "rejected_not_signer"
    REJECTED_ALREADY_SIGNED = "rejected_already_signed"
    LEGAL_COMPLETE = "legal_complete"
    FACTS_LOCKED = "facts_locked"
    NAME_CHOSEN = "name_chosen"
    CHECKLIST_UPDATED = "checklist_updated"
    SITE_BUILT = "site_built"
    SITE_DEPLOYED = "site_deployed"
    DEPLOY_OVERRIDE = "deploy_override"
    # ADR-0031
    PDF_DOWNLOADED = "pdf_downloaded"
    MEMBER_JOINED = "member_joined"
    INVITE_SENT = "invite_sent"
    PLAN_CHANGED = "plan_changed"


class AuditEntry(BaseModel):
    id: int | None = None
    case_id: str
    document_id: str | None = None
    actor: str  # founder id, user id, "system", or an AgentId value
    action: AuditAction
    from_version: int | None = None
    to_version: int | None = None
    detail: dict[str, Any] = {}
    at: datetime
