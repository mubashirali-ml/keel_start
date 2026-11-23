"""Case validation, vesting defaults and missing facts (ADR-0013). Owned by T-002.

Validation is deterministic code, never the LLM.
"""

from __future__ import annotations

from ..domain.types import CaseFacts, ValidationIssue, ValidationResult

__all__ = ["ValidationIssue", "ValidationResult", "apply_vesting_defaults", "missing_facts", "validate_facts"]


def apply_vesting_defaults(facts: CaseFacts) -> tuple[CaseFacts, list[str]]:
    """48/12 when both are missing, cliff ``min(12, vesting)`` or vesting 48 when one is; one
    founder-facing note per defaulted founder (ADR-0013, T-002)."""
    raise NotImplementedError("apply_vesting_defaults is implemented in T-002")


def missing_facts(facts: CaseFacts) -> list[str]:
    """Required fact keys still unknown, in ask order: business_description, entity_type,
    state, founders, incorporation_date (ADR-0013, T-002)."""
    raise NotImplementedError("missing_facts is implemented in T-002")


def validate_facts(facts: CaseFacts) -> ValidationResult:
    """Every ADR-0013 issue code plus missing facts and notes, on a normalised copy (T-002)."""
    raise NotImplementedError("validate_facts is implemented in T-002")
