"""Live Netlify site host: zip deploy (ADR-0011, ADR-0023). Owned by T-008."""

from __future__ import annotations

import httpx

from ..domain.website import DeployResult, SiteBundle

__all__ = ["NETLIFY_API_URL", "NetlifySiteHost"]

NETLIFY_API_URL = "https://api.netlify.com"


class NetlifySiteHost:
    """``SiteHost`` that finds or creates the site, uploads ``bundle.to_zip()`` and polls until
    ready; never raises for provider errors (``status="failed"``)."""

    name = "netlify"
    configured = True

    def __init__(self, token: str, client: httpx.Client | None = None, poll_timeout_s: float = 60) -> None:
        self.token = token
        self.client = client
        self.poll_timeout_s = poll_timeout_s

    def deploy(self, site_slug: str, bundle: SiteBundle) -> DeployResult:
        raise NotImplementedError("NetlifySiteHost.deploy is implemented in T-008")
