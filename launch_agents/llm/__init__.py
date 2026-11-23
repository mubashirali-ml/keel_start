"""LLM abstraction, deterministic fake, usage reporting and provider selection (ADR-0010, ADR-0022)."""

from __future__ import annotations

from ..config import Settings
from .fake import FakeHandler, FakeLLM, FakeLLMMissingHandler
from .provider import LLMMessage, LLMOutputError, LLMProvider, LLMRequest
from .usage import LLMUsage, report_usage, usage_sink

__all__ = [
    "FakeHandler",
    "FakeLLM",
    "FakeLLMMissingHandler",
    "LLMMessage",
    "LLMOutputError",
    "LLMProvider",
    "LLMRequest",
    "LLMUsage",
    "get_llm",
    "report_usage",
    "usage_sink",
]


def get_llm(settings: Settings) -> LLMProvider:
    """The provider chosen by ``settings.llm_provider`` (ADR-0022 selection table).

    ``load_settings`` already resolved the choice (explicit ``LLM_PROVIDER``, else the first API
    key found, else ``fake``; ``LAUNCH_FAKE_SERVICES=1`` forces ``fake``). Providers are only
    constructed here, never called.
    """
    provider = settings.llm_provider
    if provider == "fake":
        return FakeLLM()
    if provider == "claude_code":
        from .claude_code import ClaudeCodeProvider

        return ClaudeCodeProvider(settings)
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)
    if provider in ("deepseek", "groq"):
        from .openai_compat import OpenAICompatibleProvider

        return OpenAICompatibleProvider(settings, preset=provider)
    if provider == "openai-compatible":
        from .openai_compat import OpenAICompatibleProvider

        return OpenAICompatibleProvider(settings)
    raise ValueError(f"unknown LLM provider {provider!r}")  # pragma: no cover - Settings restricts it
