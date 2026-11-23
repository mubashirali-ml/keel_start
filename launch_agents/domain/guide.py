"""Registration guide types (ADR-0016)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .types import EntityType

__all__ = ["GuideLink", "GuideStep", "RegistrationGuide"]


class GuideLink(BaseModel):
    label: str
    url: str


class GuideStep(BaseModel):
    id: str  # stable across rebuilds, e.g. "formation-file", "83b-mail"
    category: Literal["name", "formation", "agent", "ein", "agreement", "83b", "domain", "ongoing"]
    title: str
    detail: str  # short plain-language markdown
    links: list[GuideLink] = []
    fee: str | None = None  # "$110": strings, as published by the state
    due: date | None = None  # e.g. the 83(b) deadline
    optional: bool = False


class RegistrationGuide(BaseModel):
    state: str
    state_name: str
    entity_type: EntityType
    full_guide: bool  # True for DE and WY
    steps: list[GuideStep]
    last_reviewed: date  # from the curated data file
    sources: list[GuideLink]
    disclaimer: str  # LEGAL_NOTICE + "The app does not file anything for you."
