"""LLM providers ``deepseek``, ``groq`` and ``openai-compatible`` (ADR-0010 behaviour,
ADR-0022 construction). Owned by T-025."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from .provider import LLMRequest, T

__all__ = ["PRESETS", "OpenAICompatibleProvider"]

# Preset base URLs and default models (ADR-0010, ADR-0022).
PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
}


class OpenAICompatibleProvider:
    """``langchain_openai.ChatOpenAI`` against an OpenAI-compatible endpoint: JSON mode, fence
    stripping, ``llm_timeout_s``, ``llm_max_retries``, ``model_for(task)`` and usage reporting."""

    def __init__(self, settings: Settings, *, preset: str | None = None, chat_model: Any = None) -> None:
        self.settings = settings
        self.preset = preset
        self.chat_model = chat_model
        self.name = preset or "openai-compatible"

    def complete(self, request: LLMRequest) -> str:
        """Text completion (ADR-0022, T-025)."""
        raise NotImplementedError("OpenAICompatibleProvider.complete is implemented in T-025")

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T:
        """JSON-mode completion validated against ``schema`` (ADR-0010, T-025)."""
        raise NotImplementedError("OpenAICompatibleProvider.complete_json is implemented in T-025")
