"""The deterministic fake LLM (ADR-0010).

Resolution per request: a queued ``script`` response for that task (FIFO), else an
explicitly registered handler, else a default handler from an agent's ``fake.py``, else
``FakeLLMMissingHandler`` (tests fail loudly rather than receive silent junk).
``complete_json`` validates the output against the schema exactly like a real provider.
"""

from __future__ import annotations

import importlib
import json
import time
from collections import defaultdict, deque
from typing import Any, Callable, Mapping, Sequence

from pydantic import BaseModel, ValidationError

from ..domain.errors import LLMOutputError
from .provider import LLMRequest, T
from .usage import LLMUsage, report_usage

__all__ = ["DEFAULT_HANDLER_MODULES", "FakeHandler", "FakeLLM", "FakeLLMMissingHandler", "load_default_handlers"]

FakeHandler = Callable[[LLMRequest], "str | dict | BaseModel"]

# Each agent ticket fills FAKE_HANDLERS in its own fake.py (T-001 creates them empty).
DEFAULT_HANDLER_MODULES: tuple[str, ...] = tuple(
    f"launch_agents.agents.{agent}.fake" for agent in ("manager", "law", "name", "website", "qa", "guide")
)


class FakeLLMMissingHandler(LookupError):
    """No script, registered handler or default handler answers this task."""


def load_default_handlers() -> dict[str, FakeHandler]:
    """Import every agent ``fake.py`` (lazily, at call time) and merge their ``FAKE_HANDLERS``."""
    handlers: dict[str, FakeHandler] = {}
    for module_name in DEFAULT_HANDLER_MODULES:
        module = importlib.import_module(module_name)
        handlers.update(getattr(module, "FAKE_HANDLERS", {}) or {})
    return handlers


class FakeLLM:
    """Deterministic ``LLMProvider`` for tests, recorded runs and the reliable demo."""

    name = "fake"
    model: str | None = None

    def __init__(self, handlers: Mapping[str, FakeHandler] | None = None, *, include_defaults: bool = True) -> None:
        self._defaults: dict[str, FakeHandler] = load_default_handlers() if include_defaults else {}
        self._handlers: dict[str, FakeHandler] = dict(handlers or {})
        self._scripts: defaultdict[str, deque[str | dict | BaseModel]] = defaultdict(deque)
        self.calls: list[LLMRequest] = []  # every request, in order

    def register(self, task: str, handler: FakeHandler) -> None:
        """Answer ``task`` with ``handler`` (beats a default handler, loses to a script)."""
        self._handlers[task] = handler

    def script(self, task: str, responses: Sequence[str | dict | BaseModel]) -> None:
        """Queue responses for ``task``; each request for it consumes the next one (FIFO)."""
        self._scripts[task].extend(responses)

    def _resolve(self, request: LLMRequest) -> str | dict | BaseModel:
        queue = self._scripts.get(request.task)
        if queue:
            return queue.popleft()
        handler = self._handlers.get(request.task) or self._defaults.get(request.task)
        if handler is None:
            raise FakeLLMMissingHandler(
                f"FakeLLM has no script, handler or default handler for task {request.task!r}"
            )
        return handler(request)

    def _call(self, request: LLMRequest, convert: Callable[[str | dict | BaseModel], Any]) -> Any:
        self.calls.append(request)
        started = time.perf_counter()
        ok = False
        try:
            result = convert(self._resolve(request))
            ok = True
            return result
        finally:
            report_usage(
                LLMUsage(
                    provider=self.name,
                    model=None,
                    task=request.task,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    ok=ok,
                )
            )

    def complete(self, request: LLMRequest) -> str:
        def to_text(output: str | dict | BaseModel) -> str:
            if isinstance(output, str):
                return output
            if isinstance(output, BaseModel):
                return output.model_dump_json()
            return json.dumps(output, default=str)

        return self._call(request, to_text)

    def complete_json(self, request: LLMRequest, schema: type[T]) -> T:
        def to_model(output: str | dict | BaseModel) -> T:
            try:
                if isinstance(output, BaseModel):
                    output = output.model_dump(mode="json")
                if isinstance(output, str):
                    output = json.loads(output)
                return schema.model_validate(output)
            except (ValueError, ValidationError) as exc:
                raise LLMOutputError(
                    "The AI service returned an answer I couldn't use. Please try again.",
                    details={"task": request.task},
                ) from exc

        return self._call(request, to_model)
