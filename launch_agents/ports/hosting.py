"""Website hosting port and fakes (ADR-0011). The live Netlify adapter is ``adapters/netlify.py`` (T-008)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.website import DeployResult, SiteBundle

__all__ = ["NOT_CONFIGURED_MESSAGE", "FakeSiteHost", "SiteHost", "UnconfiguredSiteHost"]

NOT_CONFIGURED_MESSAGE = (
    "Deploy isn't set up yet: add a NETLIFY_AUTH_TOKEN to publish. "
    "You can preview and download the site meanwhile."
)


@runtime_checkable
class SiteHost(Protocol):
    name: str  # "netlify" | "fake" | "none"
    configured: bool

    def deploy(self, site_slug: str, bundle: SiteBundle) -> DeployResult:
        """Publish the bundle; never raises for provider errors (returns ``status="failed"``)."""
        ...


class FakeSiteHost:
    """Configured fake host: ``https://{site_slug}.fake-host.test``; records every deploy.

    ``fail_next(n)`` makes the next ``n`` deploys return ``status="failed"`` (provider error path).
    """

    name = "fake"
    configured = True

    def __init__(self) -> None:
        self.deploys: list[tuple[str, SiteBundle]] = []
        self._fail_next = 0

    def fail_next(self, n: int = 1) -> None:
        self._fail_next += n

    def deploy(self, site_slug: str, bundle: SiteBundle) -> DeployResult:
        self.deploys.append((site_slug, bundle))
        if self._fail_next > 0:
            self._fail_next -= 1
            return DeployResult(
                status="failed",
                provider=self.name,
                message="The hosting provider didn't accept the deploy. Please try again in a minute.",
            )
        url = f"https://{site_slug}.fake-host.test"
        return DeployResult(
            status="deployed",
            url=url,
            deploy_id=f"fake-deploy-{len(self.deploys)}",
            provider=self.name,
            message=f"Your site is live at {url}",
        )


class UnconfiguredSiteHost:
    """No hosting token: every deploy returns ``not_configured`` with a friendly message."""

    name = "none"
    configured = False

    def deploy(self, site_slug: str, bundle: SiteBundle) -> DeployResult:
        return DeployResult(status="not_configured", provider=self.name, message=NOT_CONFIGURED_MESSAGE)
