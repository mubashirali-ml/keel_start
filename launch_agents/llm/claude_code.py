"""LLM provider ``claude_code``: the Claude Code CLI in print mode (ADR-0022). Owned by T-024.

T-001 provides the exact signatures; T-024 implements them. The constructor must not call
the CLI: ``get_llm`` constructs providers without using them.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from ..config import Settings
from .provider import LLMRequest, T

__all__ = ["ClaudeCodeProvider", "find_claude_binary"]


class ClaudeCodeProvider:
    """``LLMProvider`` over ``claude -p ... --output-format json`` for the owner's own machine.

    ADR-0022: own-machine development and live demos only; refuses production (``ConfigError``)
    and logs the terms-of-use warning once per process (T-024).
    """

    name = "claude_code"

    def __init__(
        self,
        settings: Settings,
        *,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
        binary: str | None = None,
    ) -> None:
        self.settings = settings
        self.runner = runner
        self.binary = binary

    def complete(self, request: LLMRequest) -> str:
        """Text completion through the CLI (ADR-0022, T-024)."""
        raise NotImplementedError("ClaudeCodeProvider.complete is implemented in T-024")

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T:
        """Structured completion with ``--json-schema`` (ADR-0022, T-024)."""
        raise NotImplementedError("ClaudeCodeProvider.complete_json is implemented in T-024")


def find_claude_binary(settings: Settings, *, home: Path | None = None) -> str:
    """``CLAUDE_CODE_PATH``; else the newest VS Code extension binary; else ``claude`` on PATH;
    else ``ConfigError`` explaining all three options (ADR-0022, T-024)."""
    raise NotImplementedError("find_claude_binary is implemented in T-024")
