"""Document sign-off state machine with e-signature evidence (ADR-0014, ADR-0031). Owned by T-004."""

from .machine import SignOffOutcome, create_document, edit, is_legal_complete, regenerate, sign

__all__ = ["SignOffOutcome", "create_document", "edit", "is_legal_complete", "regenerate", "sign"]
