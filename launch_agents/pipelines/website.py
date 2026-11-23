"""Build -> QA -> fix (at most ``MAX_QA_FIX_ROUNDS``) -> deploy gate (ADR-0015). Owned by T-013."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..domain.types import CaseFacts
from ..domain.website import DeployResult, QaReport, SiteBuild, SiteBundle, SiteContent
from ..llm.provider import LLMProvider
from ..ports.hosting import SiteHost

__all__ = ["PipelineResult", "build_site", "deploy_build"]


class PipelineResult(BaseModel):
    content: SiteContent
    bundle: SiteBundle
    reports: list[QaReport]
    passed: bool
    fix_rounds: int


def build_site(
    facts: CaseFacts,
    llm: LLMProvider,
    *,
    previous: SiteContent | None = None,
    change_request: str | None = None,
    now: datetime,
) -> PipelineResult:
    """Generate (or revise ``previous``), render, QA, and fix while failing (T-013)."""
    raise NotImplementedError("build_site is implemented in T-013")


def deploy_build(build: SiteBuild, host: SiteHost, site_slug: str, *, override_qa: bool) -> DeployResult:
    """``DeployBlockedError`` when QA failed and the founder did not override (T-013)."""
    raise NotImplementedError("deploy_build is implemented in T-013")
