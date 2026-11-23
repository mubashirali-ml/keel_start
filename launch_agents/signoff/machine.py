"""Pure sign-off state machine (ADR-0014 rules with the ADR-0031 changes). Owned by T-004.

Every function returns a ``SignOffOutcome`` whose ``audit`` entries must be persisted, also
for rejections; the service then raises ``outcome.error``.

The functions never mutate their inputs and do no I/O; the only clock is the injected
``now``. Rules are checked in the ADR-0014 order:

1. stale: ``version != doc.version`` or the evidence hash does not match the content being
   signed (ADR-0031) -> ``REJECTED_STALE`` + ``StaleVersionError``;
2. ``sign``: not a required signer -> ``REJECTED_NOT_SIGNER``; already signed this version ->
   ``REJECTED_ALREADY_SIGNED``; else ``SIGNED`` (and ``EXECUTED`` on the last signer);
3. ``edit``: not a required signer -> ``REJECTED_NOT_SIGNER``; unchanged content -> no-op;
   else ``REOPENED`` (if executed), ``SIGNATURES_INVALIDATED``, ``EDITED`` and, when the
   editor is the only signer, ``EXECUTED``;
4. ``regenerate``: unchanged content -> no-op; else ``REOPENED`` (if executed) and
   ``REGENERATED`` with every signature cancelled.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict

from ..domain.documents import (
    AuditAction,
    AuditEntry,
    Document,
    DocumentStatus,
    DraftDocument,
    Signature,
    SignatureEvidence,
)
from ..domain.errors import AlreadySignedError, LaunchError, NotASignerError, StaleVersionError
from ..domain.helpers import document_sha256, new_id

__all__ = ["SignOffOutcome", "create_document", "edit", "is_legal_complete", "regenerate", "sign"]

SYSTEM_ACTOR = "system"


class SignOffOutcome(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    document: Document  # unchanged when ok is False
    audit: list[AuditEntry]  # ALWAYS returned, also for rejections -> persist it
    invalidated: list[str] = []  # founder ids whose signatures were cancelled
    error: LaunchError | None = None  # StaleVersionError | NotASignerError | AlreadySignedError


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _entry(
    doc: Document,
    actor: str,
    action: AuditAction,
    now: datetime,
    *,
    from_version: int | None = None,
    to_version: int | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEntry:
    return AuditEntry(
        case_id=doc.case_id,
        document_id=doc.id,
        actor=actor,
        action=action,
        from_version=from_version,
        to_version=to_version,
        detail=dict(detail or {}),
        at=now,
    )


def _evidence_detail(evidence: SignatureEvidence) -> dict[str, Any]:
    """The ``SIGNED`` / ``EDITED`` audit detail (ADR-0031)."""
    return {
        "user_id": evidence.user_id,
        "typed_name": evidence.typed_name,
        "content_sha256": evidence.content_sha256,
        "ip": evidence.ip,
    }


def _signature(founder_id: str, version: int, evidence: SignatureEvidence, now: datetime) -> Signature:
    return Signature(
        founder_id=founder_id,
        version=version,
        signed_at=now,
        user_id=evidence.user_id,
        typed_name=evidence.typed_name,
        consent_version=evidence.consent_version,
        content_sha256=evidence.content_sha256,
        ip=evidence.ip,
        user_agent=evidence.user_agent,
        acted_by_user_id=evidence.acted_by_user_id,
    )


def _all_signed(required: Sequence[str], signatures: Sequence[Signature]) -> bool:
    signed = {s.founder_id for s in signatures}
    return bool(required) and all(f in signed for f in required)


def _reject(
    doc: Document,
    actor: str,
    action: AuditAction,
    error: LaunchError,
    now: datetime,
    *,
    detail: dict[str, Any],
) -> SignOffOutcome:
    entry = _entry(doc, actor, action, now, from_version=doc.version, to_version=doc.version, detail=detail)
    return SignOffOutcome(ok=False, document=doc, audit=[entry], invalidated=[], error=error)


def _check_stale(
    doc: Document, actor: str, version: int, content_sha256: str, expected_sha256: str, operation: str, now: datetime
) -> SignOffOutcome | None:
    """Rule 1 (ADR-0014) extended by ADR-0031: wrong version or wrong content hash."""
    if version != doc.version:
        error = StaleVersionError(
            f"This document changed to version {doc.version} while you were looking at it. "
            "Review the new version first.",
            details={"current_version": doc.version, "requested_version": version},
        )
        return _reject(
            doc, actor, AuditAction.REJECTED_STALE, error, now,
            detail={"operation": operation, "reason": "version", "requested_version": version,
                    "current_version": doc.version},
        )
    if content_sha256 != expected_sha256:
        error = StaleVersionError(
            f"This document changed while you were reviewing it. Review version {doc.version} and sign again.",
            details={"current_version": doc.version, "reason": "content_sha256"},
        )
        return _reject(
            doc, actor, AuditAction.REJECTED_STALE, error, now,
            detail={"operation": operation, "reason": "content_sha256", "content_sha256": content_sha256,
                    "expected_sha256": expected_sha256, "current_version": doc.version},
        )
    return None


def _not_signer(doc: Document, actor: str, operation: str, now: datetime) -> SignOffOutcome:
    verb = "sign" if operation == "sign" else "edit"
    error = NotASignerError(
        f"Only the founders who sign this document can {verb} it.",
        details={"founder_id": actor, "required_signers": list(doc.required_signers)},
    )
    return _reject(
        doc, actor, AuditAction.REJECTED_NOT_SIGNER, error, now,
        detail={"operation": operation, "founder_id": actor},
    )


# --------------------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------------------
def create_document(case_id: str, draft: DraftDocument, *, now: datetime) -> SignOffOutcome:
    """Version 1, awaiting signatures, ``CREATED`` audit (T-004)."""
    doc = Document(
        id=new_id("doc"),
        case_id=case_id,
        kind=draft.kind,
        title=draft.title,
        founder_id=draft.founder_id,
        version=1,
        content=draft.content,
        status=DocumentStatus.AWAITING_SIGNATURES,
        required_signers=list(draft.required_signers),
        signatures=[],
        created_at=now,
        updated_at=now,
    )
    entry = _entry(
        doc, SYSTEM_ACTOR, AuditAction.CREATED, now, to_version=1,
        detail={"kind": doc.kind.value, "title": doc.title, "content_sha256": document_sha256(doc.content),
                "required_signers": list(doc.required_signers)},
    )
    return SignOffOutcome(ok=True, document=doc, audit=[entry])


def sign(doc: Document, founder_id: str, version: int, *, evidence: SignatureEvidence, now: datetime) -> SignOffOutcome:
    """Record a signature bound to ``evidence.content_sha256``; executes on the last one (T-004)."""
    stale = _check_stale(doc, founder_id, version, evidence.content_sha256, document_sha256(doc.content), "sign", now)
    if stale is not None:
        return stale
    if founder_id not in doc.required_signers:
        return _not_signer(doc, founder_id, "sign", now)
    if any(s.founder_id == founder_id and s.version == doc.version for s in doc.signatures):
        error = AlreadySignedError(
            f"You have already signed version {doc.version} of this document.",
            details={"founder_id": founder_id, "version": doc.version},
        )
        return _reject(
            doc, founder_id, AuditAction.REJECTED_ALREADY_SIGNED, error, now,
            detail={"operation": "sign", "founder_id": founder_id},
        )

    signatures = [s.model_copy(deep=True) for s in doc.signatures]
    signatures.append(_signature(founder_id, doc.version, evidence, now))
    audit = [
        _entry(doc, founder_id, AuditAction.SIGNED, now, from_version=doc.version, to_version=doc.version,
               detail=_evidence_detail(evidence))
    ]
    status = doc.status
    if _all_signed(doc.required_signers, signatures):
        status = DocumentStatus.EXECUTED
        audit.append(
            _entry(doc, founder_id, AuditAction.EXECUTED, now, from_version=doc.version, to_version=doc.version,
                   detail={"signers": [s.founder_id for s in signatures]})
        )
    new_doc = doc.model_copy(deep=True, update={"signatures": signatures, "status": status, "updated_at": now})
    return SignOffOutcome(ok=True, document=new_doc, audit=audit)


def edit(
    doc: Document, editor_id: str, version: int, new_content: str, *, evidence: SignatureEvidence, now: datetime
) -> SignOffOutcome:
    """New version; other signatures cancelled; the editor signs the new content (T-004)."""
    new_sha = document_sha256(new_content)
    stale = _check_stale(doc, editor_id, version, evidence.content_sha256, new_sha, "edit", now)
    if stale is not None:
        return stale
    if editor_id not in doc.required_signers:
        return _not_signer(doc, editor_id, "edit", now)
    if new_sha == document_sha256(doc.content):
        # Unchanged (line endings are not a change, ADR-0031 hash rule): no-op, no audit.
        return SignOffOutcome(ok=True, document=doc, audit=[])

    old_v, new_v = doc.version, doc.version + 1
    audit: list[AuditEntry] = []
    if doc.status == DocumentStatus.EXECUTED:
        audit.append(_entry(doc, editor_id, AuditAction.REOPENED, now, from_version=old_v, to_version=new_v,
                            detail={"reason": "edited"}))
    invalidated = [s.founder_id for s in doc.signatures if s.founder_id != editor_id]
    if invalidated:
        audit.append(_entry(doc, editor_id, AuditAction.SIGNATURES_INVALIDATED, now, from_version=old_v,
                            to_version=new_v, detail={"founders": list(invalidated)}))
    audit.append(_entry(doc, editor_id, AuditAction.EDITED, now, from_version=old_v, to_version=new_v,
                        detail=_evidence_detail(evidence)))

    signatures = [_signature(editor_id, new_v, evidence, now)]
    status = DocumentStatus.AWAITING_SIGNATURES
    if _all_signed(doc.required_signers, signatures):
        status = DocumentStatus.EXECUTED
        audit.append(_entry(doc, editor_id, AuditAction.EXECUTED, now, from_version=new_v, to_version=new_v,
                            detail={"signers": [editor_id]}))
    new_doc = doc.model_copy(
        deep=True,
        update={"version": new_v, "content": new_content, "signatures": signatures, "status": status,
                "updated_at": now},
    )
    return SignOffOutcome(ok=True, document=new_doc, audit=audit, invalidated=invalidated)


def regenerate(doc: Document, draft: DraftDocument, *, now: datetime, actor: str = "system") -> SignOffOutcome:
    """Facts changed after drafting: new version, all signatures cancelled (T-004).

    The draft must be the same document (same ``kind`` and ``founder_id``), else ``ValueError``
    (a caller bug, not a founder-facing rejection). Its title, content and required signers
    replace the document's; identical content (by ``document_sha256``) is a no-op.
    """
    if draft.kind != doc.kind or draft.founder_id != doc.founder_id:
        raise ValueError(
            f"regenerate: draft ({draft.kind.value}, {draft.founder_id}) is not document "
            f"{doc.id} ({doc.kind.value}, {doc.founder_id})"
        )
    new_sha = document_sha256(draft.content)
    if new_sha == document_sha256(doc.content):
        return SignOffOutcome(ok=True, document=doc, audit=[])

    old_v, new_v = doc.version, doc.version + 1
    invalidated = [s.founder_id for s in doc.signatures]
    audit: list[AuditEntry] = []
    if doc.status == DocumentStatus.EXECUTED:
        audit.append(_entry(doc, actor, AuditAction.REOPENED, now, from_version=old_v, to_version=new_v,
                            detail={"reason": "regenerated"}))
    audit.append(_entry(doc, actor, AuditAction.REGENERATED, now, from_version=old_v, to_version=new_v,
                        detail={"founders": list(invalidated), "content_sha256": new_sha}))
    new_doc = doc.model_copy(
        deep=True,
        update={"version": new_v, "title": draft.title, "content": draft.content,
                "required_signers": list(draft.required_signers), "signatures": [],
                "status": DocumentStatus.AWAITING_SIGNATURES, "updated_at": now},
    )
    return SignOffOutcome(ok=True, document=new_doc, audit=audit, invalidated=invalidated)


def is_legal_complete(docs: Sequence[Document]) -> bool:
    """Non-empty and every document executed (T-004)."""
    items = list(docs)
    return bool(items) and all(d.status == DocumentStatus.EXECUTED for d in items)
