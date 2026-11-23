"""Shared request-body helpers (ADR-0033 input validation). Owned by T-016.

Route modules define their own bodies on ``StrictBody`` (``extra="forbid"``) with the
ADR-0033 length limits.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["StrictBody"]


class StrictBody(BaseModel):
    """Base for every request body: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")
