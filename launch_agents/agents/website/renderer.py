"""Deterministic static-site renderer (ADR-0015). Owned by T-008."""

from __future__ import annotations

from ...domain.types import CaseFacts
from ...domain.website import SiteBundle, SiteContent

__all__ = ["render_site", "required_pages"]


def render_site(content: SiteContent) -> SiteBundle:
    """One ``<slug>.html`` per page plus ``styles.css``; pure and byte-for-byte deterministic (T-008)."""
    raise NotImplementedError("render_site is implemented in T-008")


def required_pages(facts: CaseFacts) -> list[str]:
    """``facts.website.pages`` or ``DEFAULT_SITE_PAGES`` (T-008)."""
    raise NotImplementedError("required_pages is implemented in T-008")
