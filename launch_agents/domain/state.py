"""Agent working memory per case and the stored case record (ADR-0008, ADR-0027)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from .messages import AgentId
from .types import CaseFacts

__all__ = [
    "CaseRecord",
    "CaseState",
    "DomainCheck",
    "DomainStatus",
    "LegalIssue",
    "NameCandidate",
    "StateNameCheck",
]


class DomainStatus(str, Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    UNKNOWN = "unknown"


class DomainCheck(BaseModel):
    domain: str
    status: DomainStatus
    source: str  # "rdap" | "fake"
    checked_at: datetime
    detail: str | None = None


class StateNameCheck(BaseModel):
    state: str
    status: Literal["check_manually"] = "check_manually"
    search_url: str
    office_url: str


class NameCandidate(BaseModel):
    name: str
    rationale: str
    domains: list[DomainCheck]
    state_check: StateNameCheck | None
    trademark_search_url: str


class LegalIssue(BaseModel):
    code: str
    severity: Literal["info", "warning"]
    message: str


class CaseState(BaseModel):
    active_agent: AgentId = AgentId.MANAGER
    facts_locked: bool = False
    facts_locked_at: datetime | None = None
    pending_fact: str | None = None  # key the Manager last asked for
    notices_given: list[str] = []  # e.g. "default_vesting:f1", shown once
    name_candidates: list[NameCandidate] = []
    chosen_domain: str | None = None
    legal_issues: list[LegalIssue] = []


class CaseRecord(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    facts: CaseFacts
    state: CaseState
    created_by: str | None = None  # user id of the creator (ADR-0027)
    billing_user_id: str | None = None  # whose plan the company uses (ADR-0030)
