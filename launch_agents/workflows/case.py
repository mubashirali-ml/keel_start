"""``CaseService``: companies per account, the conversation, actions, names, checklist and
progress (ADR-0017 progress rules, ADR-0032 signatures). Owned by T-014."""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from ..agents.base import AgentDeps, TurnHandler
from ..domain.accounts import CaseAccess, RequestContext
from ..domain.helpers import utcnow
from ..domain.messages import ChatMessage
from ..domain.state import NameCandidate
from ..domain.views import CaseSummary, CaseView, GuideView, PostMessageResult
from ..persistence.repository import Repository
from ..ports.entitlements import EntitlementsProvider
from ..ports.jobs import JobRunner
from ..security.pii import ScrubResult
from ..team.service import TeamService
from .ports import LegalServicePort, WebsiteServicePort

__all__ = ["CaseService"]


class CaseService:
    def __init__(
        self,
        repo: Repository,
        team: TeamService,
        *,
        turn_handler: TurnHandler,
        agent_deps: Callable[[CaseAccess], AgentDeps],
        legal: LegalServicePort,
        website: WebsiteServicePort,
        jobs: JobRunner,
        entitlements: EntitlementsProvider,
        scrubber: Callable[[str], ScrubResult],
        clock: Callable[[], datetime] = utcnow,
        today: Callable[[], date] | None = None,
    ) -> None:
        self.repo = repo
        self.team = team
        self.turn_handler = turn_handler
        self.agent_deps = agent_deps
        self.legal = legal
        self.website = website
        self.jobs = jobs
        self.entitlements = entitlements
        self.scrubber = scrubber
        self.clock = clock
        self.today = today

    def create_case(self, ctx: RequestContext) -> CaseView:
        """Creator = OWNER + billing user; stores the greeting; ``PlanRequiredError`` beyond
        ``max_companies``."""
        raise NotImplementedError("CaseService.create_case is implemented in T-014")

    def list_cases(self, ctx: RequestContext) -> list[CaseSummary]:
        """Member companies only."""
        raise NotImplementedError("CaseService.list_cases is implemented in T-014")

    def get_view(self, access: CaseAccess) -> CaseView:
        raise NotImplementedError("CaseService.get_view is implemented in T-014")

    def list_messages(self, access: CaseAccess, after_seq: int | None = None) -> list[ChatMessage]:
        raise NotImplementedError("CaseService.list_messages is implemented in T-014")

    def post_message(self, access: CaseAccess, text: str) -> PostMessageResult:
        """Scrub -> store -> turn -> save -> store agent messages -> execute actions (jobs)."""
        raise NotImplementedError("CaseService.post_message is implemented in T-014")

    def choose_name(self, access: CaseAccess, name: str, domain: str | None = None) -> CaseView:
        raise NotImplementedError("CaseService.choose_name is implemented in T-014")

    def recheck_names(self, access: CaseAccess) -> list[NameCandidate]:
        raise NotImplementedError("CaseService.recheck_names is implemented in T-014")

    def get_guide(self, access: CaseAccess) -> GuideView:
        raise NotImplementedError("CaseService.get_guide is implemented in T-014")

    def set_guide_item(self, access: CaseAccess, item_id: str, done: bool) -> GuideView:
        raise NotImplementedError("CaseService.set_guide_item is implemented in T-014")

    def delete_case(self, access: CaseAccess) -> None:
        """Needs ``DELETE_COMPANY``."""
        raise NotImplementedError("CaseService.delete_case is implemented in T-014")
