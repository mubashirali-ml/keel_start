"""The LangGraph turn graph: extract -> validate -> route -> handover -> respond -> hand_back
(ADR-0009). Owned by T-012."""

from __future__ import annotations

from typing import Any

from ..agents.base import AgentDeps, TurnInput, TurnResult

__all__ = ["build_graph", "handle_turn"]


def build_graph(deps: AgentDeps) -> Any:
    """The compiled ``StateGraph`` (no checkpointer) for one set of dependencies (T-012)."""
    raise NotImplementedError("build_graph is implemented in T-012")


def handle_turn(turn: TurnInput, deps: AgentDeps) -> TurnResult:
    """One founder turn: at most one specialist and two handoff messages (T-012)."""
    raise NotImplementedError("handle_turn is implemented in T-012")
