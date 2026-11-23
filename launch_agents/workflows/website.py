"""``WebsiteService``: builds and deploys as tracked jobs (ADR-0015, ADR-0028, ADR-0032). Owned by T-013."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..domain.accounts import Actor, CaseAccess
from ..domain.helpers import utcnow
from ..domain.jobs import JobRecord
from ..domain.views import SiteBuildOutcome
from ..domain.website import SiteBuild, SiteFile
from ..llm.provider import LLMProvider
from ..persistence.repository import Repository
from ..ports.hosting import SiteHost
from ..ports.jobs import JobRegistry, JobRunner

__all__ = ["WebsiteService", "register_website_jobs"]


class WebsiteService:
    """Implements ``WebsiteServicePort``. ``llm_for(case_id)`` returns the (metered) LLM for
    that company."""

    def __init__(
        self,
        repo: Repository,
        llm_for: Callable[[str], LLMProvider],
        host: SiteHost,
        jobs: JobRunner,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.repo = repo
        self.llm_for = llm_for
        self.host = host
        self.jobs = jobs
        self.clock = clock

    def request_build(self, access: CaseAccess, change_request: str | None = None) -> JobRecord:
        raise NotImplementedError("WebsiteService.request_build is implemented in T-013")

    def request_deploy(self, access: CaseAccess, *, override_qa: bool = False) -> JobRecord:
        raise NotImplementedError("WebsiteService.request_deploy is implemented in T-013")

    def run_build(self, case_id: str, change_request: str | None, actor: Actor) -> SiteBuildOutcome:
        raise NotImplementedError("WebsiteService.run_build is implemented in T-013")

    def run_deploy(self, case_id: str, actor: Actor, *, override_qa: bool) -> SiteBuildOutcome:
        raise NotImplementedError("WebsiteService.run_deploy is implemented in T-013")

    def latest(self, access: CaseAccess) -> SiteBuild | None:
        raise NotImplementedError("WebsiteService.latest is implemented in T-013")

    def preview_file(self, access: CaseAccess, path: str) -> SiteFile:
        raise NotImplementedError("WebsiteService.preview_file is implemented in T-013")

    def download_zip(self, access: CaseAccess) -> bytes:
        raise NotImplementedError("WebsiteService.download_zip is implemented in T-013")


def register_website_jobs(registry: JobRegistry, service: WebsiteService) -> None:
    """Register the ``website.build`` and ``website.deploy`` handlers (T-013)."""
    raise NotImplementedError("register_website_jobs is implemented in T-013")
