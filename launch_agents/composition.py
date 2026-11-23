"""The composition root: the only place that chooses concrete providers and adapters from
``Settings`` (ADR-0024, ADR-0032). ``Services`` is real (T-001); ``build_services`` is T-016's."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from .accounts.service import AuthService
from .admin.service import AdminService
from .billing.service import BillingService
from .config import Settings
from .llm.provider import LLMProvider
from .persistence.accounts import AccountsRepository
from .persistence.repository import Repository
from .persistence.team import TeamRepository
from .ports.domain_check import DomainChecker
from .ports.email import Mailer
from .ports.entitlements import EntitlementsProvider
from .ports.hosting import SiteHost
from .ports.jobs import JobRegistry, JobRunner
from .ports.notifications import Notifier
from .ports.payments import PaymentGateway
from .privacy.service import PrivacyService
from .security.rate_limit import RateLimiter
from .team.service import TeamService
from .workflows.case import CaseService
from .workflows.ports import LegalServicePort, WebsiteServicePort

__all__ = ["Services", "build_services"]


@dataclass
class Services:
    settings: Settings
    engine: Engine
    repo: Repository
    accounts: AccountsRepository
    team_repo: TeamRepository
    auth: AuthService
    team: TeamService
    billing: BillingService
    entitlements: EntitlementsProvider
    case: CaseService
    legal: LegalServicePort
    website: WebsiteServicePort
    jobs: JobRunner
    job_registry: JobRegistry
    mailer: Mailer
    notifier: Notifier
    privacy: PrivacyService
    admin: AdminService
    limiter: RateLimiter
    llm: LLMProvider
    domain_checker: DomainChecker
    host: SiteHost
    payments: PaymentGateway


def build_services(settings: Settings, *, jobs: JobRunner | None = None) -> Services:
    """Wire every service, adapter and job handler from ``settings``; migrate the database via
    ``init_db`` outside production; an injected ``jobs`` runner (e.g. ``InlineJobRunner``)
    replaces ``DbJobRunner`` (ADR-0032, T-016)."""
    raise NotImplementedError("build_services is implemented in T-016")
