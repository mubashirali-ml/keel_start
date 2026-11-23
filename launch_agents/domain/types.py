"""Case facts, patches and validation result types (ADR-0008, ADR-0013)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

__all__ = [
    "CaseFacts",
    "EntityType",
    "FactsPatch",
    "Founder",
    "FounderPatch",
    "ValidationIssue",
    "ValidationResult",
    "WebsitePatch",
    "WebsiteRequirements",
    "apply_patch",
]


class EntityType(str, Enum):
    LLC = "LLC"
    C_CORP = "Delaware C-Corp"


class Founder(BaseModel):
    id: str  # "f1", "f2", ... assigned in order of first mention, never reused
    name: str
    email: str
    equity_percent: Decimal  # 0 < x <= 100, at most EQUITY_DECIMALS places (validated by rules)
    vesting_months: int | None = None  # None = not stated; rules apply the default
    cliff_months: int | None = None


class WebsiteRequirements(BaseModel):
    pages: list[str] = []  # page names the founder asked for; empty -> DEFAULT_SITE_PAGES
    services: list[str] = []
    about: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_address: str | None = None  # public business address, shown on the website
    extra_content: list[str] = []  # "must include" items; QA checks each one
    style_notes: str | None = None


class CaseFacts(BaseModel):
    business_description: str | None = None
    founders: list[Founder] = []
    entity_type: EntityType | None = None
    state: str | None = None  # USPS code, "DE", "WY", ...
    incorporation_date: date | None = None
    name_preferences: list[str] = []
    company_name: str | None = None
    website: WebsiteRequirements = WebsiteRequirements()


class FounderPatch(BaseModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    equity_percent: Decimal | None = None
    vesting_months: int | None = None
    cliff_months: int | None = None


class WebsitePatch(BaseModel):
    """Every field optional; lists replace, scalars overwrite."""

    pages: list[str] | None = None
    services: list[str] | None = None
    about: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_address: str | None = None
    extra_content: list[str] | None = None
    style_notes: str | None = None


class FactsPatch(BaseModel):
    business_description: str | None = None
    founders: list[FounderPatch] | None = None
    remove_founder_ids: list[str] = []
    entity_type: EntityType | None = None
    state: str | None = None
    incorporation_date: date | None = None
    name_preferences: list[str] | None = None
    company_name: str | None = None
    website: WebsitePatch | None = None


class ValidationIssue(BaseModel):
    code: str
    field: str
    message: str
    founder_id: str | None = None


class ValidationResult(BaseModel):
    ok: bool  # no issues and nothing required missing
    issues: list[ValidationIssue]
    missing: list[str]  # required fact keys still unknown, in ask order
    facts: CaseFacts  # normalised copy with vesting defaults applied
    notes: list[str]  # founder-facing notes, e.g. default vesting


_FOUNDER_ID = re.compile(r"^f(\d+)$")
_SCALAR_FIELDS = ("business_description", "entity_type", "incorporation_date", "company_name")


def _founder_number(founder_id: str) -> int:
    match = _FOUNDER_ID.match(founder_id)
    return int(match.group(1)) if match else 0


def _find_founder(founders: list[Founder], patch: FounderPatch) -> int | None:
    if patch.id is not None:
        for i, f in enumerate(founders):
            if f.id == patch.id:
                return i
    if patch.email and patch.email.strip():
        email = patch.email.strip().casefold()
        for i, f in enumerate(founders):
            if f.email and f.email.strip().casefold() == email:
                return i
    if patch.name and patch.name.strip():
        name = " ".join(patch.name.split()).casefold()
        for i, f in enumerate(founders):
            if " ".join(f.name.split()).casefold() == name:
                return i
    return None


def apply_patch(facts: CaseFacts, patch: FactsPatch) -> CaseFacts:
    """Merge ``patch`` into a copy of ``facts`` (pure; ADR-0008).

    - ``None`` fields leave values unchanged; lists replace, scalars overwrite.
    - ``remove_founder_ids`` are removed first, then each ``FounderPatch`` matches an existing
      founder by ``id``, else by case-insensitive email, else by case-insensitive name;
      otherwise a new founder is appended with the next free id. Ids are never renumbered or
      reused: the next id is one above the highest id the facts had before this patch
      (``f1``, ``f3`` + new -> ``f4``). A new founder needs a ``name`` (a nameless unknown
      founder patch is ignored); missing email/equity stay ``""`` / ``Decimal(0)`` and are
      reported by validation.
    - ``state`` is stripped and upper-cased; ``entity_type == C_CORP`` forces ``state = "DE"``.
    """
    data = facts.model_copy(deep=True)

    for field in _SCALAR_FIELDS:
        value = getattr(patch, field)
        if value is not None:
            setattr(data, field, value)
    if patch.state is not None:
        data.state = patch.state.strip().upper()
    if patch.name_preferences is not None:
        data.name_preferences = list(patch.name_preferences)

    if patch.website is not None:
        website = data.website.model_copy(deep=True)
        for field, value in patch.website.model_dump(exclude_none=True).items():
            setattr(website, field, list(value) if isinstance(value, list) else value)
        data.website = website

    founders = list(data.founders)
    next_number = max((_founder_number(f.id) for f in founders), default=0) + 1
    if patch.remove_founder_ids:
        removed = set(patch.remove_founder_ids)
        founders = [f for f in founders if f.id not in removed]
    for fp in patch.founders or []:
        index = _find_founder(founders, fp)
        if index is None:
            if not (fp.name and fp.name.strip()):
                continue
            founders.append(
                Founder(
                    id=f"f{next_number}",
                    name=fp.name.strip(),
                    email=(fp.email or "").strip(),
                    equity_percent=fp.equity_percent if fp.equity_percent is not None else Decimal(0),
                    vesting_months=fp.vesting_months,
                    cliff_months=fp.cliff_months,
                )
            )
            next_number += 1
            continue
        current = founders[index]
        updates = fp.model_dump(exclude_none=True, exclude={"id"})
        if "name" in updates:
            updates["name"] = updates["name"].strip()
        if "email" in updates:
            updates["email"] = updates["email"].strip()
        founders[index] = current.model_copy(update=updates)
    data.founders = founders

    if data.entity_type == EntityType.C_CORP:
        data.state = "DE"
    return data
