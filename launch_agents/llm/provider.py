"""The LLM provider interface (ADR-0010; providers in ADR-0022).

``complete_json`` contract (every implementation): the output is validated with
``schema.model_validate``; on invalid output a real provider retries once with the
validation error appended; a second failure raises ``LLMOutputError``. Network/auth errors
raise ``LLMOutputError`` too. Agents catch it and answer politely (ADR-0009).
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from ..domain.errors import LLMOutputError

__all__ = ["LLMMessage", "LLMOutputError", "LLMProvider", "LLMRequest", "T"]


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    task: str  # dotted task name from the ADR-0010 catalog, e.g. "name.suggest"
    messages: list[LLMMessage]
    context: dict[str, Any] = {}  # structured inputs; real providers ignore it, the fake reads it
    temperature: float = 0.2
    max_tokens: int | None = None


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    name: str  # "fake" | "claude_code" | "anthropic" | "deepseek" | "groq" | "openai-compatible"

    def complete(self, request: LLMRequest) -> str: ...

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T: ...
