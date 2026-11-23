"""Live RDAP domain checker (ADR-0011, ADR-0023). Owned by T-007."""

from __future__ import annotations

import httpx

from ..domain.state import DomainCheck

__all__ = ["IANA_BOOTSTRAP_URL", "RDAP_FALLBACK_URL", "RdapDomainChecker"]

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
RDAP_FALLBACK_URL = "https://rdap.org/domain/{domain}"


class RdapDomainChecker:
    """``DomainChecker`` over RDAP: 200 -> taken, 404 -> available, anything else -> unknown
    with a short detail. Never raises for lookup failures (ADR-0011)."""

    name = "rdap"

    def __init__(self, client: httpx.Client | None = None, timeout_s: float = 5.0) -> None:
        self.client = client
        self.timeout_s = timeout_s

    def check(self, domain: str) -> DomainCheck:
        raise NotImplementedError("RdapDomainChecker.check is implemented in T-007")
