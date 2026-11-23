"""Admin area: metadata only, never company content (ADR-0034, ADR-0038). Owned by T-038."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from ..domain.accounts import User
from ..domain.billing import PlanId, PriceCheck, SupportLevel
from ..domain.helpers import utcnow
from ..domain.jobs import JobRecord, JobStatus
from ..persistence.accounts import AccountsRepository
from ..persistence.admin import AdminQueries
from ..ports.jobs import JobRunner

__all__ = [
    "AdminCaseRow",
    "AdminService",
    "AdminUsageRow",
    "AdminUserRow",
    "OutboxEmailRow",
    "Page",
    "SystemInfo",
]

RowT = TypeVar("RowT")


class Page(BaseModel, Generic[RowT]):
    items: list[RowT]
    page: int
    page_size: int
    total: int


class AdminUserRow(BaseModel):
    user_id: str
    email: str
    full_name: str
    created_at: datetime
    email_verified: bool
    plan: PlanId
    support: SupportLevel
    companies: int
    last_seen_at: datetime | None = None


class AdminCaseRow(BaseModel):
    case_id: str
    company_name: str | None
    members: int
    created_at: datetime
    facts_locked: bool
    documents_executed: bool
    site_published: bool
    plan: PlanId


class AdminUsageRow(BaseModel):
    user_id: str
    email: str
    plan: PlanId
    calls: int
    input_tokens: int
    output_tokens: int
    limit: int


class OutboxEmailRow(BaseModel):
    id: str
    to_masked: str  # "a***@example.com"
    template: str
    status: str
    error: str | None = None
    created_at: datetime
    sent_at: datetime | None = None


class SystemInfo(BaseModel):
    """Providers and configured services, migration status, worker heartbeat and price checks;
    never a secret value."""

    llm_provider: str
    llm_models: dict[str, str]
    domain_checker: str
    hosting_provider: str
    hosting_configured: bool
    email_provider: str
    payments_mode: str  # "fake" | "stripe-test" | "stripe-live"
    schema_current: bool | None
    last_worker_heartbeat: datetime | None
    price_checks: list[PriceCheck]


class AdminService:
    def __init__(
        self,
        queries: AdminQueries,
        jobs: JobRunner,
        accounts: AccountsRepository,
        *,
        clock: Callable[[], datetime] = utcnow,
        price_checks: Callable[[], list[PriceCheck]] | None = None,
    ) -> None:
        self.queries = queries
        self.jobs_runner = jobs
        self.accounts = accounts
        self.clock = clock
        self.price_checks = price_checks

    def users(self, *, query: str | None, page: int, plan: PlanId | None = None) -> Page[AdminUserRow]:
        raise NotImplementedError("AdminService.users is implemented in T-038")

    def companies(self, *, query: str | None, page: int) -> Page[AdminCaseRow]:
        raise NotImplementedError("AdminService.companies is implemented in T-038")

    def usage(self, *, month: str) -> list[AdminUsageRow]:
        raise NotImplementedError("AdminService.usage is implemented in T-038")

    def jobs(self, *, status: JobStatus | None, page: int) -> Page[JobRecord]:
        raise NotImplementedError("AdminService.jobs is implemented in T-038")

    def emails(self, *, status: str | None, page: int) -> Page[OutboxEmailRow]:
        raise NotImplementedError("AdminService.emails is implemented in T-038")

    def system(self) -> SystemInfo:
        raise NotImplementedError("AdminService.system is implemented in T-038")

    def retry_job(self, admin: User, job_id: str) -> JobRecord:
        """Re-queue a failed job; written to ``admin_audit``."""
        raise NotImplementedError("AdminService.retry_job is implemented in T-038")
