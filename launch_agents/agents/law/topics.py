"""Keyword helpers shared by the Law Agent and its fake LLM handlers (T-006).

Deterministic: the fake ``law.intent`` handler classifies with these, and the agent uses
``normalise_topic`` to map whatever a real model returns onto the known topics.
"""

from __future__ import annotations

import re

__all__ = ["DRAFT_KEYWORDS", "TOPICS", "TOPIC_TITLES", "detect_topic", "is_draft_request", "normalise_topic"]

# The topics the Law Agent explains (ADR-0010 task law.answer, T-006 criterion 8).
TOPICS: tuple[str, ...] = (
    "entity_choice",
    "state",
    "liability",
    "operating_agreement",
    "tax",
    "vesting",
    "83b",
    "general",
)

TOPIC_TITLES: dict[str, str] = {
    "entity_choice": "LLC or C-Corp",
    "state": "choice of state",
    "liability": "liability protection",
    "operating_agreement": "operating agreement basics",
    "tax": "tax treatment",
    "vesting": "founder vesting",
    "83b": "the 83(b) election",
    "general": "general legal questions",
}

DRAFT_KEYWORDS: tuple[str, ...] = ("draft", "documents", "paperwork", "prepare")
_DRAFT_RE = re.compile(r"\b(draft\w*|documents?|paperwork|prepar\w*)\b", re.IGNORECASE)

# First match wins, so the more specific topics come first.
_TOPIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("83b", re.compile(r"83\s*\(?\s*b\s*\)?", re.IGNORECASE)),
    ("vesting", re.compile(r"\b(vest\w*|cliff\w*)\b", re.IGNORECASE)),
    ("operating_agreement", re.compile(r"\boperating\s+agreements?\b|\bbylaws?\b", re.IGNORECASE)),
    ("tax", re.compile(r"\b(tax\w*|irs|pass[- ]through|double\s+taxation)\b", re.IGNORECASE)),
    ("liability", re.compile(r"\b(liab\w*|personal(ly)?\s+assets?|sued|lawsuits?|protect\w*)\b", re.IGNORECASE)),
    ("entity_choice", re.compile(r"\b(llcs?|c[- ]?corps?|corporations?|entity|entities|s[- ]?corps?)\b",
                                 re.IGNORECASE)),
    ("state", re.compile(r"\b(states?|delaware|wyoming|nevada|incorporate\s+in|form\s+in)\b", re.IGNORECASE)),
)


def is_draft_request(text: str) -> bool:
    """True when the founder asks for documents to be drafted ("draft", "documents",
    "paperwork", "prepare")."""
    return bool(_DRAFT_RE.search(text or ""))


def detect_topic(text: str) -> str:
    """The topic a question is about, by keywords; ``"general"`` when nothing matches."""
    for topic, pattern in _TOPIC_PATTERNS:
        if pattern.search(text or ""):
            return topic
    return "general"


def normalise_topic(topic: str | None, text: str = "") -> str:
    """Map a model-supplied topic onto ``TOPICS``: exact ids pass, other strings are
    classified by keywords, and a missing topic falls back to the question text."""
    if topic:
        key = topic.strip().lower().replace("-", "_").replace(" ", "_")
        if key in TOPICS:
            return key
        aliases = {"83(b)": "83b", "83_b": "83b", "83(b)_election": "83b", "entity": "entity_choice",
                   "state_choice": "state", "taxes": "tax"}
        if key in aliases:
            return aliases[key]
        found = detect_topic(topic)
        if found != "general":
            return found
    return detect_topic(text)
