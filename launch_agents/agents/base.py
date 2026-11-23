"""The specialist contract and the turn types (ADR-0009). Implemented in T-001.

Agents never import ``persistence``, ``workflows``, ``api`` or any account/billing module;
they get everything through ``AgentContext`` and return ``AgentReply``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel

from ..domain.messages import AgentAction, AgentId, ChatMessage
from ..domain.state import CaseState
from ..domain.types import CaseFacts, FactsPatch
from ..llm.provider import LLMProvider
from ..ports.domain_check import DomainChecker

__all__ = [
    "AgentContext",
    "AgentDeps",
    "AgentReply",
    "AgentServices",
    "Specialist",
    "TurnHandler",
    "TurnInput",
    "TurnResult",
]


@dataclass(frozen=True)
class AgentServices:
    domain_checker: DomainChecker  # ADR-0011


@dataclass(frozen=True)
class AgentContext:
    case_id: str
    facts: CaseFacts
    state: CaseState
    history: list[ChatMessage]  # last 20 messages, oldest first, excluding founder_text
    founder_text: str
    founder_id: str | None
    today: date
    llm: LLMProvider  # ADR-0010
    services: AgentServices


class AgentReply(BaseModel):
    messages: list[ChatMessage] = []  # every message has role=AGENT and agent=<this agent>
    facts_patch: FactsPatch | None = None
    state: CaseState | None = None  # full replacement of CaseState when not None
    actions: list[AgentAction] = []
    hand_back: bool = False  # task done; return the chat to the Manager


@runtime_checkable
class Specialist(Protocol):
    agent_id: AgentId

    def handle(self, ctx: AgentContext) -> AgentReply: ...


class TurnInput(BaseModel):
    case_id: str
    facts: CaseFacts
    state: CaseState
    history: list[ChatMessage]
    founder_text: str
    founder_id: str | None
    today: date


class TurnResult(BaseModel):
    messages: list[ChatMessage]  # new agent messages in order (not the founder's)
    facts: CaseFacts
    state: CaseState
    actions: list[AgentAction]


@dataclass(frozen=True)
class AgentDeps:
    llm: LLMProvider
    services: AgentServices
    specialists: Mapping[AgentId, Specialist] | None = None  # None -> the four real ones


TurnHandler = Callable[[TurnInput, AgentDeps], TurnResult]
