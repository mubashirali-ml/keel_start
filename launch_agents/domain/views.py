"""Response views shared by services, the API and the frontend (ADR-0017 as extended by
ADR-0032 and ADR-0038). The frontend's ``types.ts`` mirrors these field for field."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from .accounts import MemberRole, User
from .billing import Plan, PlanId, Subscription, UsageSummary
from .documents import Document
from .guide import RegistrationGuide
from .jobs import JobRecord
from .messages import AgentId, ChatMessage
from .state import LegalIssue
from .types import CaseFacts, ValidationIssue
from .website import SiteBuild

__all__ = [
    "BillingOverview",
    "CaseSummary",
    "CaseView",
    "DocumentsOutcome",
    "EditOutcome",
    "EditRequest",
    "GuideView",
    "InvitePreview",
    "MeView",
    "MemberView",
    "PostMessageResult",
    "Progress",
    "PublicConfig",
    "SignRequest",
    "SiteBuildOutcome",
    "SiteJobOutcome",
    "StepId",
    "StepProgress",
    "StepStatus",
]


class StepId(str, Enum):
    FACTS = "facts"
    NAME = "name"
    LEGAL = "legal"
    CAP_TABLE = "cap_table"
    WEBSITE = "website"
    REGISTRATION = "registration"


class StepStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ATTENTION = "attention"


class StepProgress(BaseModel):
    id: StepId
    label: str
    status: StepStatus
    detail: str


class Progress(BaseModel):
    steps: list[StepProgress]
    percent: int  # done steps * 100 // 6


class CaseView(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    facts: CaseFacts
    facts_locked: bool
    active_agent: AgentId
    company_name: str | None
    chosen_domain: str | None
    validation_issues: list[ValidationIssue]
    missing_facts: list[str]
    deadline_83b: date | None
    days_until_83b: int | None
    progress: Progress
    legal_issues: list[LegalIssue]
    # ADR-0032 additions
    my_role: MemberRole | None
    my_founder_id: str | None
    plan: PlanId  # the company's entitlements
    active_jobs: list[JobRecord]


class CaseSummary(BaseModel):
    id: str
    company_name: str | None
    created_at: datetime
    updated_at: datetime
    percent: int


class GuideView(BaseModel):
    guide: RegistrationGuide
    done: dict[str, bool]
    done_count: int
    total: int


class PostMessageResult(BaseModel):
    messages: list[ChatMessage]  # the founder's message first, then every new message
    case: CaseView
    open_view: str | None  # last OpenView action, a UI hint
    jobs: list[JobRecord] = []  # jobs enqueued by this turn (ADR-0032)


class DocumentsOutcome(BaseModel):
    documents: list[Document]
    messages: list[ChatMessage]


class EditOutcome(BaseModel):
    document: Document
    invalidated: list[str]


class SiteBuildOutcome(BaseModel):
    build: SiteBuild
    messages: list[ChatMessage]


class SiteJobOutcome(BaseModel):
    job: JobRecord
    build: SiteBuild | None


class MeView(BaseModel):
    user: User
    plan: PlanId
    subscription: Subscription
    email_verified: bool
    companies: list[CaseSummary]
    csrf_token: str


class MemberView(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: MemberRole
    founder_id: str | None
    founder_name: str | None
    joined_at: datetime


class InvitePreview(BaseModel):
    company_name: str | None
    inviter_name: str
    email_hint: str  # "a***@example.com"
    founder_name: str | None
    expired: bool


class PublicConfig(BaseModel):
    brand_name: str
    demo_mode: bool
    payments_test_mode: bool
    hosting_configured: bool
    plans: list[Plan]
    esign_consent_text: str
    esign_consent_version: str
    support_email: str | None  # ADR-0038
    yearly_enabled: bool  # ADR-0038


class BillingOverview(BaseModel):
    subscription: Subscription
    plan: Plan
    usage: UsageSummary
    can_switch_plan: bool  # an active paid subscription exists


class SignRequest(BaseModel):
    version: int
    content_sha256: str
    typed_name: str
    consent: Literal[True]


class EditRequest(SignRequest):
    content: str
