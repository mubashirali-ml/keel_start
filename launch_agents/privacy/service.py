"""Export all my data and delete my account (ADR-0034). Owned by T-037."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from pydantic import BaseModel

from ..billing.service import BillingService
from ..config import Settings
from ..domain.accounts import User
from ..domain.helpers import utcnow
from ..persistence.accounts import AccountsRepository
from ..persistence.privacy import PrivacyQueries
from ..persistence.repository import Repository
from ..persistence.team import TeamRepository

__all__ = ["DeletionReport", "PrivacyService"]


class DeletionReport(BaseModel):
    """What an account deletion removed and what it kept for the co-founders."""

    user_id: str
    deleted_companies: list[str] = []  # companies where the user was the only member
    kept_companies: list[str] = []  # companies handed over to the remaining co-founders
    subscription_cancelled: bool = False
    notes: list[str] = []  # friendly lines shown to the user


class PrivacyService:
    def __init__(
        self,
        queries: PrivacyQueries,
        repo: Repository,
        team: TeamRepository,
        accounts: AccountsRepository,
        billing: BillingService,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.queries = queries
        self.repo = repo
        self.team = team
        self.accounts = accounts
        self.billing = billing
        self.settings = settings
        self.clock = clock

    def export_zip(self, user: User) -> tuple[str, bytes]:
        """``({brand slug}-export-{date}.zip, bytes)`` with only this user's data (T-037)."""
        raise NotImplementedError("PrivacyService.export_zip is implemented in T-037")

    def delete_account(self, user: User, *, password: str, confirm: str) -> DeletionReport:
        """Password re-entry and ``confirm == "DELETE"``; cancels billing, hands companies over (T-037)."""
        raise NotImplementedError("PrivacyService.delete_account is implemented in T-037")
