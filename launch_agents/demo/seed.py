"""Seeded demo companies and users, played through the real services with fakes (ADR-0036). Owned by T-016."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..domain.billing import PlanId

__all__ = ["DEMO_STAGES", "SeedResult", "seed_case"]

DEMO_STAGES = ("account", "new", "facts", "names", "legal", "signed", "website", "complete")


@dataclass
class SeedResult:
    case_id: str | None
    users: dict[str, str] = field(default_factory=dict)  # "alice" -> email


def seed_case(settings: Settings, stage: str, *, plan: PlanId = PlanId.LAUNCH) -> SeedResult:
    """Every stage up to ``stage`` (cumulative); refuses unless ``settings.fake_services`` (T-016)."""
    raise NotImplementedError("seed_case is implemented in T-016")
