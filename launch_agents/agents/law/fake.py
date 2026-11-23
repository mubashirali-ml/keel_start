"""Default fake-LLM handlers for the law agent's tasks (ADR-0010).

T-001 creates this empty; T-006 fills it. Handlers must be pure functions of the request and
derive their answers from ``request.context`` so the demo journey reads naturally.
"""

from __future__ import annotations

from ...llm.fake import FakeHandler

__all__ = ["FAKE_HANDLERS"]

FAKE_HANDLERS: dict[str, FakeHandler] = {}
