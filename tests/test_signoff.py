"""T-004: sign-off state machine with e-signature evidence (ADR-0014, ADR-0031)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from launch_agents.domain.constants import ESIGN_CONSENT_VERSION
from launch_agents.domain.documents import (
    AuditAction,
    Document,
    DocumentKind,
    DocumentStatus,
    DraftDocument,
    SignatureEvidence,
)
from launch_agents.domain.errors import AlreadySignedError, NotASignerError, StaleVersionError
from launch_agents.domain.helpers import document_sha256
from launch_agents.signoff import SignOffOutcome, create_document, edit, is_legal_complete, regenerate, sign

T0 = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)
CASE = "case_abc"
A, B = "f_alice", "f_bob"
NAMES = {A: "Alice Chen", B: "Bob Diaz"}
V1 = "# Founder IP Assignment Agreement\n\nVersion one text.\n"
V2 = "# Founder IP Assignment Agreement\n\nVersion two text, edited.\n"


def t(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def ev(founder: str, content: str, *, ip: str = "203.0.113.7", sha: str | None = None) -> SignatureEvidence:
    return SignatureEvidence(
        user_id=f"u_{founder}",
        typed_name=NAMES.get(founder, founder),
        consent_version=ESIGN_CONSENT_VERSION,
        content_sha256=sha if sha is not None else document_sha256(content),
        ip=ip,
        user_agent="pytest-agent/1.0",
        acted_by_user_id=None,
    )


def draft(content: str = V1, signers: list[str] | None = None, *, kind: DocumentKind = DocumentKind.IP_ASSIGNMENT,
          founder_id: str | None = None, title: str = "Founder IP Assignment Agreement") -> DraftDocument:
    return DraftDocument(kind=kind, title=title, founder_id=founder_id, content=content,
                         required_signers=list(signers if signers is not None else [A, B]))


def actions(outcome: SignOffOutcome) -> list[AuditAction]:
    return [e.action for e in outcome.audit]


def created(content: str = V1, signers: list[str] | None = None, **kw) -> Document:
    return create_document(CASE, draft(content, signers, **kw), now=T0).document


def executed_two_signer() -> Document:
    doc = created()
    doc = sign(doc, A, 1, evidence=ev(A, V1), now=t(1)).document
    out = sign(doc, B, 1, evidence=ev(B, V1), now=t(2))
    assert out.document.status == DocumentStatus.EXECUTED
    return out.document


def election_83b() -> Document:
    return created("# IRS 83(b) Election - Alice\n", [A], kind=DocumentKind.ELECTION_83B, founder_id=A,
                   title="IRS 83(b) Election - Alice Chen")


# ---------------------------------------------------------------------------------- AC1
def test_create_document_is_v1_awaiting_with_created_entry():
    out = create_document(CASE, draft(), now=T0)
    doc = out.document
    assert out.ok is True and out.error is None and out.invalidated == []
    assert doc.version == 1 and doc.status == DocumentStatus.AWAITING_SIGNATURES and doc.signatures == []
    assert doc.case_id == CASE and doc.kind == DocumentKind.IP_ASSIGNMENT and doc.content == V1
    assert doc.required_signers == [A, B] and doc.created_at == T0 and doc.updated_at == T0
    assert doc.id.startswith("doc_")
    assert actions(out) == [AuditAction.CREATED]
    entry = out.audit[0]
    assert entry.case_id == CASE and entry.document_id == doc.id and entry.at == T0 and entry.to_version == 1
    assert entry.detail["content_sha256"] == document_sha256(V1)


def test_create_document_ids_are_unique_and_draft_not_mutated():
    d = draft()
    before = d.model_dump()
    one, two = create_document(CASE, d, now=T0), create_document(CASE, d, now=T0)
    assert one.document.id != two.document.id
    assert d.model_dump() == before
    one.document.required_signers.append("x")
    assert d.required_signers == [A, B]


# ---------------------------------------------------------------------------------- AC2
def test_two_signers_first_sign_awaits_second_executes():
    doc = created()
    e = ev(A, V1)
    first = sign(doc, A, 1, evidence=e, now=t(1))
    assert first.ok and first.error is None
    assert first.document.status == DocumentStatus.AWAITING_SIGNATURES
    assert actions(first) == [AuditAction.SIGNED]
    signed = first.audit[0]
    assert signed.actor == A and signed.document_id == doc.id and signed.at == t(1)
    assert signed.detail == {"user_id": "u_f_alice", "typed_name": "Alice Chen",
                             "content_sha256": document_sha256(V1), "ip": "203.0.113.7"}
    [sig] = first.document.signatures
    assert sig.founder_id == A and sig.version == 1 and sig.signed_at == t(1)
    assert (sig.user_id, sig.typed_name, sig.consent_version, sig.content_sha256, sig.ip, sig.user_agent,
            sig.acted_by_user_id) == (e.user_id, e.typed_name, e.consent_version, e.content_sha256, e.ip,
                                      e.user_agent, e.acted_by_user_id)
    assert first.document.updated_at == t(1)

    second = sign(first.document, B, 1, evidence=ev(B, V1), now=t(2))
    assert second.ok and second.document.status == DocumentStatus.EXECUTED
    assert actions(second) == [AuditAction.SIGNED, AuditAction.EXECUTED]
    assert [s.founder_id for s in second.document.signatures] == [A, B]
    assert second.document.version == 1
    # inputs untouched
    assert doc.signatures == [] and len(first.document.signatures) == 1


def test_sign_records_demo_mode_actor():
    doc = created()
    e = ev(A, V1).model_copy(update={"acted_by_user_id": "u_demo_operator"})
    sig = sign(doc, A, 1, evidence=e, now=t(1)).document.signatures[0]
    assert sig.acted_by_user_id == "u_demo_operator"


# ---------------------------------------------------------------------------------- AC3
def test_sign_with_wrong_content_hash_is_rejected_stale():
    doc = created()
    out = sign(doc, A, 1, evidence=ev(A, V1, sha=document_sha256(V2)), now=t(1))
    assert out.ok is False and isinstance(out.error, StaleVersionError)
    assert out.document == doc and out.document.signatures == []
    assert actions(out) == [AuditAction.REJECTED_STALE]
    assert out.audit[0].actor == A and out.audit[0].detail["reason"] == "content_sha256"


def test_hash_ignores_line_endings():
    doc = created()
    out = sign(doc, A, 1, evidence=ev(A, V1.replace("\n", "\r\n")), now=t(1))
    assert out.ok


# ---------------------------------------------------------------------------------- AC4
def test_edit_by_a_cancels_b_and_a_signs_new_content():
    # Two signers who both signed -> the document is executed, so the edit also reopens it (rule 5).
    doc = executed_two_signer()
    e = ev(A, V2, ip="198.51.100.4")
    out = edit(doc, A, 1, V2, evidence=e, now=t(3))
    assert out.ok and out.error is None
    new = out.document
    assert new.version == 2 and new.content == V2 and new.status == DocumentStatus.AWAITING_SIGNATURES
    [sig] = new.signatures
    assert sig.founder_id == A and sig.version == 2 and sig.signed_at == t(3)
    assert sig.content_sha256 == document_sha256(V2) and sig.ip == "198.51.100.4"
    assert out.invalidated == [B]
    assert actions(out) == [AuditAction.REOPENED, AuditAction.SIGNATURES_INVALIDATED, AuditAction.EDITED]
    inv = out.audit[1]
    assert inv.detail == {"founders": [B]}
    edited = out.audit[2]
    assert (edited.from_version, edited.to_version, edited.actor) == (1, 2, A)
    assert edited.detail == {"user_id": "u_f_alice", "typed_name": "Alice Chen",
                             "content_sha256": document_sha256(V2), "ip": "198.51.100.4"}
    # original untouched
    assert doc.version == 1 and len(doc.signatures) == 2 and doc.content == V1


def test_edit_on_awaiting_document_signed_by_both_of_three():
    doc = created(signers=[A, B, "f_cara"])
    doc = sign(doc, A, 1, evidence=ev(A, V1), now=t(1)).document
    doc = sign(doc, B, 1, evidence=ev(B, V1), now=t(2)).document
    assert doc.status == DocumentStatus.AWAITING_SIGNATURES
    out = edit(doc, A, 1, V2, evidence=ev(A, V2), now=t(3))
    assert actions(out) == [AuditAction.SIGNATURES_INVALIDATED, AuditAction.EDITED]
    assert out.invalidated == [B] and out.audit[0].detail == {"founders": [B]}
    assert [s.founder_id for s in out.document.signatures] == [A]
    assert out.document.version == 2 and out.document.status == DocumentStatus.AWAITING_SIGNATURES


def test_edit_by_unsigned_editor_with_nobody_to_invalidate():
    doc = created()
    out = edit(doc, B, 1, V2, evidence=ev(B, V2), now=t(1))
    assert out.ok and out.invalidated == [] and actions(out) == [AuditAction.EDITED]
    assert [s.founder_id for s in out.document.signatures] == [B]


def test_edit_with_evidence_for_old_content_is_stale():
    doc = created()
    doc = sign(doc, A, 1, evidence=ev(A, V1), now=t(1)).document
    out = edit(doc, A, 1, V2, evidence=ev(A, V1), now=t(2))  # hash of the OLD content
    assert out.ok is False and isinstance(out.error, StaleVersionError)
    assert out.document == doc and actions(out) == [AuditAction.REJECTED_STALE]
    assert out.invalidated == []


# ---------------------------------------------------------------------------------- AC5
def test_edit_of_executed_document_reopens():
    doc = executed_two_signer()
    out = edit(doc, B, 1, V2, evidence=ev(B, V2), now=t(5))
    assert actions(out)[0] == AuditAction.REOPENED
    assert out.document.status == DocumentStatus.AWAITING_SIGNATURES and out.invalidated == [A]
    assert out.audit[0].from_version == 1 and out.audit[0].to_version == 2


def test_single_signer_83b_edit_executes_again_immediately():
    doc = election_83b()
    doc = sign(doc, A, 1, evidence=ev(A, doc.content), now=t(1)).document
    assert doc.status == DocumentStatus.EXECUTED
    new_text = "# IRS 83(b) Election - Alice\n\nCorrected.\n"
    out = edit(doc, A, 1, new_text, evidence=ev(A, new_text), now=t(2))
    assert out.ok and out.document.status == DocumentStatus.EXECUTED and out.document.version == 2
    assert actions(out) == [AuditAction.REOPENED, AuditAction.EDITED, AuditAction.EXECUTED]
    assert out.invalidated == []
    [sig] = out.document.signatures
    assert sig.version == 2 and sig.content_sha256 == document_sha256(new_text)


def test_83b_not_signable_or_editable_by_other_founder():
    doc = election_83b()
    s = sign(doc, B, 1, evidence=ev(B, doc.content), now=t(1))
    e = edit(doc, B, 1, V2, evidence=ev(B, V2), now=t(1))
    for out in (s, e):
        assert out.ok is False and isinstance(out.error, NotASignerError)
        assert actions(out) == [AuditAction.REJECTED_NOT_SIGNER] and out.document == doc


# ---------------------------------------------------------------------------------- AC6
@pytest.mark.parametrize("op", ["sign", "edit"])
def test_wrong_version_is_rejected_stale_and_names_current_version(op):
    doc = created()
    doc = edit(doc, A, 1, V2, evidence=ev(A, V2), now=t(1)).document
    assert doc.version == 2
    snapshot = doc.model_dump()
    if op == "sign":
        out = sign(doc, B, 1, evidence=ev(B, V2), now=t(2))
    else:
        out = edit(doc, B, 1, V2 + "more\n", evidence=ev(B, V2 + "more\n"), now=t(2))
    assert out.ok is False and out.document == doc and doc.model_dump() == snapshot
    assert isinstance(out.error, StaleVersionError)
    assert "version 2" in out.error.message and out.error.code == "stale_version"
    assert out.error.details["current_version"] == 2
    assert actions(out) == [AuditAction.REJECTED_STALE]
    entry = out.audit[0]
    assert entry.actor == B and entry.document_id == doc.id and entry.at == t(2)
    assert entry.detail["requested_version"] == 1 and entry.detail["operation"] == op


def test_stale_is_checked_before_not_signer():
    doc = created()
    out = sign(doc, "f_stranger", 7, evidence=ev("f_stranger", V1), now=t(1))
    assert isinstance(out.error, StaleVersionError)


# ---------------------------------------------------------------------------------- AC7
def test_non_signer_is_rejected():
    doc = created()
    out = sign(doc, "f_stranger", 1, evidence=ev("f_stranger", V1), now=t(1))
    assert out.ok is False and isinstance(out.error, NotASignerError) and out.document == doc
    assert actions(out) == [AuditAction.REJECTED_NOT_SIGNER] and out.audit[0].actor == "f_stranger"


def test_signing_twice_is_rejected():
    doc = sign(created(), A, 1, evidence=ev(A, V1), now=t(1)).document
    out = sign(doc, A, 1, evidence=ev(A, V1), now=t(2))
    assert out.ok is False and isinstance(out.error, AlreadySignedError) and out.document == doc
    assert actions(out) == [AuditAction.REJECTED_ALREADY_SIGNED]
    assert len(out.document.signatures) == 1


def test_signing_executed_document_again_is_already_signed():
    doc = executed_two_signer()
    out = sign(doc, A, 1, evidence=ev(A, V1), now=t(5))
    assert isinstance(out.error, AlreadySignedError)


def test_edit_with_identical_content_is_noop():
    doc = sign(created(), A, 1, evidence=ev(A, V1), now=t(1)).document
    out = edit(doc, B, 1, V1, evidence=ev(B, V1), now=t(2))
    assert out.ok is True and out.error is None and out.audit == [] and out.invalidated == []
    assert out.document == doc and out.document.version == 1


def test_edit_differing_only_in_line_endings_is_noop():
    doc = created()
    crlf = V1.replace("\n", "\r\n")
    out = edit(doc, A, 1, crlf, evidence=ev(A, crlf), now=t(1))
    assert out.ok and out.audit == [] and out.document == doc


# ---------------------------------------------------------------------------------- AC8
def test_regenerate_cancels_all_signatures_and_bumps_version():
    doc = sign(created(), A, 1, evidence=ev(A, V1), now=t(1)).document
    out = regenerate(doc, draft(V2), now=t(2))
    assert out.ok and out.document.version == 2 and out.document.content == V2
    assert out.document.signatures == [] and out.invalidated == [A]
    assert out.document.status == DocumentStatus.AWAITING_SIGNATURES
    assert actions(out) == [AuditAction.REGENERATED]
    entry = out.audit[0]
    assert entry.actor == "system" and (entry.from_version, entry.to_version) == (1, 2)
    assert entry.detail["founders"] == [A]
    assert len(doc.signatures) == 1 and doc.version == 1


def test_regenerate_executed_reopens_with_custom_actor():
    doc = executed_two_signer()
    out = regenerate(doc, draft(V2), now=t(5), actor="law")
    assert actions(out) == [AuditAction.REOPENED, AuditAction.REGENERATED]
    assert all(e.actor == "law" for e in out.audit)
    assert out.invalidated == [A, B] and out.document.status == DocumentStatus.AWAITING_SIGNATURES


def test_regenerate_takes_new_signers_and_title_from_draft():
    doc = created()
    out = regenerate(doc, draft(V2, [A, B, "f_cara"], title="Founder IP Assignment Agreement (3)"), now=t(1))
    assert out.document.required_signers == [A, B, "f_cara"]
    assert out.document.title == "Founder IP Assignment Agreement (3)"


def test_regenerate_identical_content_is_noop():
    doc = executed_two_signer()
    out = regenerate(doc, draft(V1), now=t(5))
    assert out.ok and out.audit == [] and out.invalidated == [] and out.document == doc


def test_regenerate_rejects_a_draft_for_another_document():
    doc = created()
    with pytest.raises(ValueError):
        regenerate(doc, draft(V2, kind=DocumentKind.BYLAWS_SUMMARY), now=t(1))


def test_document_executes_after_regenerate_and_both_sign():
    doc = regenerate(executed_two_signer(), draft(V2), now=t(5)).document
    doc = sign(doc, A, 2, evidence=ev(A, V2), now=t(6)).document
    out = sign(doc, B, 2, evidence=ev(B, V2), now=t(7))
    assert out.document.status == DocumentStatus.EXECUTED
    assert all(s.version == 2 for s in out.document.signatures)


# ---------------------------------------------------------------------------------- AC9
def test_is_legal_complete():
    done = executed_two_signer()
    waiting = created()
    assert is_legal_complete([]) is False
    assert is_legal_complete([waiting]) is False
    assert is_legal_complete([done, waiting]) is False
    assert is_legal_complete([done, done]) is True
    assert is_legal_complete(tuple([done])) is True


def test_is_legal_complete_does_not_mutate_inputs():
    docs = [executed_two_signer(), created()]
    before = [d.model_dump() for d in docs]
    is_legal_complete(docs)
    assert [d.model_dump() for d in docs] == before and len(docs) == 2


def test_rejections_never_mutate_inputs():
    doc = sign(created(), A, 1, evidence=ev(A, V1), now=t(1)).document
    snapshot = doc.model_dump()
    sign(doc, A, 1, evidence=ev(A, V1), now=t(2))
    sign(doc, "x", 1, evidence=ev("x", V1), now=t(2))
    sign(doc, B, 9, evidence=ev(B, V1), now=t(2))
    edit(doc, B, 1, V2, evidence=ev(B, V2), now=t(2))
    regenerate(doc, draft(V2), now=t(2))
    assert doc.model_dump() == snapshot


def test_every_audit_entry_is_for_the_document():
    doc = created()
    outs = [create_document(CASE, draft(), now=T0)]
    outs.append(sign(doc, A, 1, evidence=ev(A, V1), now=t(1)))
    outs.append(sign(doc, A, 5, evidence=ev(A, V1), now=t(1)))
    for out in outs[1:]:
        for e in out.audit:
            assert e.case_id == CASE and e.document_id == doc.id and e.id is None
