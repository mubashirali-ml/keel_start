"""T-004 feature run: one IP-assignment document for Alice and Bob through the sign-off machine.

Run: bash scripts/py.sh evidence/T-004/feature_run.py   (recorded by scripts/record_run.sh T-004)
Steps: create; Alice signs v1 with evidence; Bob edits (Alice's signature cancelled, Bob's new
evidence on v2); Alice tries v1 (stale); Alice tries v2 with the v1 hash (stale); Alice signs v2
(executed); a regenerate reopens it. Prints status, version, signatures with evidence and the
audit after each step, asserts each, and exits non-zero on failure. No I/O besides stdout.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from launch_agents.domain.constants import ESIGN_CONSENT_VERSION  # noqa: E402
from launch_agents.domain.documents import (  # noqa: E402
    AuditAction,
    AuditEntry,
    DocumentKind,
    DocumentStatus,
    DraftDocument,
    SignatureEvidence,
)
from launch_agents.domain.errors import StaleVersionError  # noqa: E402
from launch_agents.domain.helpers import document_sha256  # noqa: E402
from launch_agents.signoff import SignOffOutcome, create_document, edit, is_legal_complete, regenerate, sign  # noqa: E402

T0 = datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc)
CASE = "case_feature_t004"
ALICE, BOB = "f_alice", "f_bob"
USERS = {ALICE: ("u_alice", "Alice Chen", "203.0.113.10"), BOB: ("u_bob", "Bob Diaz", "198.51.100.20")}

V1 = (
    "# Founder IP Assignment Agreement\n\n"
    "Each founder of [COMPANY NAME] assigns to the company all intellectual property related to its business.\n"
)
V2 = V1 + "\nBob's clarification: prior open-source contributions are excluded.\n"
V3 = V2 + "\nRegenerated: equity split changed to 60/40.\n"

FULL_AUDIT: list[AuditEntry] = []
FAILURES: list[str] = []


def check(cond: bool, what: str) -> None:
    print(f"    [{'ok' if cond else 'FAIL'}] {what}")
    if not cond:
        FAILURES.append(what)


def evidence(founder: str, content_hash: str) -> SignatureEvidence:
    user_id, name, ip = USERS[founder]
    return SignatureEvidence(user_id=user_id, typed_name=name, consent_version=ESIGN_CONSENT_VERSION,
                             content_sha256=content_hash, ip=ip, user_agent="FeatureRun/1.0")


def show(step: str, call: str, out: SignOffOutcome) -> SignOffOutcome:
    FULL_AUDIT.extend(out.audit)
    d = out.document
    print(f"\n=== {step}")
    print(f"  call:        {call}")
    print(f"  ok:          {out.ok}")
    print(f"  error:       {type(out.error).__name__ + ': ' + out.error.message if out.error else None}")
    print(f"  status:      {d.status.value}")
    print(f"  version:     {d.version}   content sha256: {document_sha256(d.content)[:16]}...")
    print(f"  invalidated: {out.invalidated}")
    print("  signatures:")
    for s in d.signatures or []:
        print(f"    - {s.founder_id} v{s.version} at {s.signed_at.isoformat()} user={s.user_id} "
              f"name={s.typed_name!r} consent={s.consent_version} ip={s.ip} ua={s.user_agent} "
              f"sha256={s.content_sha256[:16]}...")
    if not d.signatures:
        print("    (none)")
    print("  audit (this step):")
    for e in out.audit:
        print(f"    - {e.at.isoformat()} {e.actor:8} {e.action.value:24} v{e.from_version}->v{e.to_version} {e.detail}")
    if not out.audit:
        print("    (none)")
    return out


def main() -> int:
    h1, h2 = document_sha256(V1), document_sha256(V2)
    print("T-004 feature run: sign-off state machine with e-signature evidence")
    print(f"  case={CASE}  signers={[ALICE, BOB]}  consent_version={ESIGN_CONSENT_VERSION}")
    print(f"  sha256(v1)={h1}\n  sha256(v2)={h2}")

    draft = DraftDocument(kind=DocumentKind.IP_ASSIGNMENT, title="Founder IP Assignment Agreement",
                          founder_id=None, content=V1, required_signers=[ALICE, BOB])

    # 1. create
    out = show("1. create", "create_document(case, draft, now=T0)", create_document(CASE, draft, now=T0))
    doc = out.document
    check(out.ok and doc.version == 1 and doc.status == DocumentStatus.AWAITING_SIGNATURES, "v1, awaiting")
    check(doc.signatures == [] and [e.action for e in out.audit] == [AuditAction.CREATED], "no signatures, one created entry")

    # 2. Alice signs v1
    out = show("2. Alice signs v1", "sign(doc, alice, 1, evidence=<Alice, sha(v1)>)",
               sign(doc, ALICE, 1, evidence=evidence(ALICE, h1), now=T0 + timedelta(minutes=1)))
    doc = out.document
    check(out.ok and doc.status == DocumentStatus.AWAITING_SIGNATURES, "still awaiting Bob")
    sig = doc.signatures[0]
    check((sig.founder_id, sig.version, sig.typed_name, sig.consent_version, sig.content_sha256, sig.ip)
          == (ALICE, 1, "Alice Chen", ESIGN_CONSENT_VERSION, h1, "203.0.113.10"), "signature carries the evidence")
    check(out.audit[0].action == AuditAction.SIGNED
          and set(out.audit[0].detail) == {"user_id", "typed_name", "content_sha256", "ip"}, "signed entry detail")

    # 3. Bob edits -> v2, Alice's signature cancelled, Bob signs v2
    out = show("3. Bob edits v1 -> v2", "edit(doc, bob, 1, V2, evidence=<Bob, sha(v2)>)",
               edit(doc, BOB, 1, V2, evidence=evidence(BOB, h2), now=T0 + timedelta(minutes=2)))
    doc = out.document
    check(out.ok and doc.version == 2 and doc.status == DocumentStatus.AWAITING_SIGNATURES, "v2, awaiting")
    check(out.invalidated == [ALICE], "Alice's signature cancelled")
    check([(s.founder_id, s.version, s.content_sha256) for s in doc.signatures] == [(BOB, 2, h2)],
          "only Bob's signature, on v2, bound to the new content")
    check([e.action for e in out.audit] == [AuditAction.SIGNATURES_INVALIDATED, AuditAction.EDITED]
          and out.audit[0].detail == {"founders": [ALICE]}
          and (out.audit[1].from_version, out.audit[1].to_version) == (1, 2), "invalidated + edited 1->2")

    # 4. Alice tries the old version number
    before = doc
    out = show("4. Alice signs v1 (stale version)", "sign(doc, alice, 1, evidence=<Alice, sha(v1)>)",
               sign(doc, ALICE, 1, evidence=evidence(ALICE, h1), now=T0 + timedelta(minutes=3)))
    check(not out.ok and isinstance(out.error, StaleVersionError) and "version 2" in out.error.message,
          "StaleVersionError naming version 2")
    check(out.document == before and [e.action for e in out.audit] == [AuditAction.REJECTED_STALE],
          "document unchanged, rejected_stale entry")

    # 5. Alice uses v2 but the hash of v1
    out = show("5. Alice signs v2 with the v1 hash (stale content)", "sign(doc, alice, 2, evidence=<Alice, sha(v1)>)",
               sign(doc, ALICE, 2, evidence=evidence(ALICE, h1), now=T0 + timedelta(minutes=4)))
    check(not out.ok and isinstance(out.error, StaleVersionError), "StaleVersionError on hash mismatch")
    check(out.document == before and [e.action for e in out.audit] == [AuditAction.REJECTED_STALE],
          "document unchanged, rejected_stale entry")

    # 6. Alice signs v2 properly -> executed
    out = show("6. Alice signs v2", "sign(doc, alice, 2, evidence=<Alice, sha(v2)>)",
               sign(doc, ALICE, 2, evidence=evidence(ALICE, h2), now=T0 + timedelta(minutes=5)))
    doc = out.document
    check(out.ok and doc.status == DocumentStatus.EXECUTED, "executed")
    check([e.action for e in out.audit] == [AuditAction.SIGNED, AuditAction.EXECUTED], "signed + executed entries")
    check(all(s.version == 2 and s.content_sha256 == h2 for s in doc.signatures) and len(doc.signatures) == 2,
          "both signatures on v2 with the v2 hash")
    check(is_legal_complete([doc]), "is_legal_complete([doc]) is True")

    # 7. Facts changed -> regenerate reopens it
    regen = draft.model_copy(update={"content": V3})
    out = show("7. regenerate (facts changed)", "regenerate(doc, draft(V3), actor='law')",
               regenerate(doc, regen, now=T0 + timedelta(minutes=6), actor="law"))
    doc = out.document
    check(out.ok and doc.version == 3 and doc.status == DocumentStatus.AWAITING_SIGNATURES and doc.signatures == [],
          "v3, awaiting, no signatures")
    check([e.action for e in out.audit] == [AuditAction.REOPENED, AuditAction.REGENERATED], "reopened + regenerated")
    check(sorted(out.invalidated) == [ALICE, BOB], "all signatures cancelled")
    check(not is_legal_complete([doc]) and not is_legal_complete([]), "legal no longer complete; empty list is False")

    print("\n=== full audit trail")
    for e in FULL_AUDIT:
        print(f"  {e.at.isoformat()} {e.actor:8} {e.action.value:24} v{e.from_version}->v{e.to_version}")
    check([e.action.value for e in FULL_AUDIT] == [
        "created", "signed", "signatures_invalidated", "edited", "rejected_stale", "rejected_stale",
        "signed", "executed", "reopened", "regenerated",
    ], "10 audit entries in order, rejections included")

    print()
    if FAILURES:
        print(f"FEATURE RUN FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("FEATURE RUN PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
