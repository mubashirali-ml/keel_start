"""LLM provider ``anthropic``: the official SDK with ``ANTHROPIC_API_KEY`` (ADR-0022). Owned by T-025.

The ``anthropic`` package is imported lazily (inside the implementation), so this module
imports cleanly without it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..config import Settings
from .provider import LLMRequest, T

if TYPE_CHECKING:  # pragma: no cover
    import anthropic

__all__ = ["DEFAULT_ANTHROPIC_MODEL", "AnthropicProvider"]

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"


class AnthropicProvider:
    """``LLMProvider`` for production (ADR-0022): model ``settings.model_for(task)`` or
    ``claude-opus-5-5``, structured outputs for ``complete_json``, refusal fallback, usage reported."""

    name = "anthropic"

    def __init__(self, settings: Settings, *, client: "anthropic.Anthropic | None" = None) -> None:
        self.settings = settings
        self.client: Any = client

    def complete(self, request: LLMRequest) -> str:
        """Text completion (ADR-0022, T-025)."""
        raise NotImplementedError("AnthropicProvider.complete is implemented in T-025")

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T:
        """Structured completion validated against ``schema`` (ADR-0022, T-025)."""
        raise NotImplementedError("AnthropicProvider.complete_json is implemented in T-025")
