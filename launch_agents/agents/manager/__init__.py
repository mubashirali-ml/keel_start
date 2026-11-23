"""Manager Agent (ADR-0009): greeting (T-001), fact gathering and routing (T-012)."""

from .agent import ManagerAgent, ManagerExtraction, RouteDecision, facts_summary, next_question
from .greeting import manager_greeting

__all__ = [
    "ManagerAgent",
    "ManagerExtraction",
    "RouteDecision",
    "facts_summary",
    "manager_greeting",
    "next_question",
]
