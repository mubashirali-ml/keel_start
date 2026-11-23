"""Sensitive-data scrubber for founder chat text (ADR-0033). Owned by T-032."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

__all__ = ["ScrubResult", "scrub"]


class ScrubResult(BaseModel):
    text: str
    redactions: list[Literal["ssn", "itin", "ein", "card"]]


def scrub(text: str) -> ScrubResult:
    """Replace SSNs, ITINs, EINs and Luhn-valid card numbers with ``[removed: SSN]`` etc.,
    before the text is stored or sent to an LLM (T-032)."""
    raise NotImplementedError("scrub is implemented in T-032")
