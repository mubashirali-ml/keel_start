"""Domain availability port and fake (ADR-0011). The live RDAP adapter is ``adapters/rdap.py`` (T-007)."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, Protocol, runtime_checkable

from ..domain.helpers import utcnow
from ..domain.state import DomainCheck, DomainStatus

__all__ = ["DEFAULT_FAKE_TAKEN", "DomainChecker", "FakeDomainChecker"]

DEFAULT_FAKE_TAKEN = frozenset({"acme.com", "launch.com", "startup.com", "google.com", "apple.com"})


@runtime_checkable
class DomainChecker(Protocol):
    name: str  # "rdap" | "fake"

    def check(self, domain: str) -> DomainCheck:
        """Availability of one domain; never raises for lookup failures (they are ``unknown``)."""
        ...


class FakeDomainChecker:
    """``taken`` for domains in ``taken``, ``unknown`` for ``unknown``, otherwise ``available``."""

    name = "fake"

    def __init__(
        self,
        taken: Iterable[str] = DEFAULT_FAKE_TAKEN,
        unknown: Iterable[str] = (),
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.taken = frozenset(d.strip().lower() for d in taken)
        self.unknown = frozenset(d.strip().lower() for d in unknown)
        self.clock = clock
        self.calls: list[str] = []

    def check(self, domain: str) -> DomainCheck:
        key = domain.strip().lower()
        self.calls.append(key)
        if key in self.taken:
            status, detail = DomainStatus.TAKEN, None
        elif key in self.unknown:
            status, detail = DomainStatus.UNKNOWN, "registry did not answer"
        else:
            status, detail = DomainStatus.AVAILABLE, None
        return DomainCheck(domain=key, status=status, source="fake", checked_at=self.clock(), detail=detail)
