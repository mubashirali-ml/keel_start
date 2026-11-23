"""Pure helpers shared by every ticket (ADR-0008, ADR-0031). Implemented in T-001."""

from __future__ import annotations

import calendar
import hashlib
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from .constants import ELECTION_83B_DAYS

__all__ = [
    "add_months",
    "days_until",
    "deadline_83b",
    "document_sha256",
    "domain_label",
    "names_match",
    "new_id",
    "slugify",
    "utcnow",
]

_COMPANY_SUFFIXES = frozenset({"llc", "inc", "corp", "co", "corporation", "incorporated", "company", "ltd"})


def deadline_83b(incorporation_date: date) -> date:
    """IRS 83(b) deadline: incorporation date + ``ELECTION_83B_DAYS`` calendar days (ADR-0013).

    Not moved for weekends or holidays; the guide tells founders to file early.
    """
    return incorporation_date + timedelta(days=ELECTION_83B_DAYS)


def days_until(deadline: date, today: date) -> int:
    """Whole days from ``today`` to ``deadline``; negative once the deadline has passed."""
    return (deadline - today).days


def add_months(d: date, months: int) -> date:
    """Add calendar months, clamping the day to the month end (Jan 31 + 1 = Feb 28/29)."""
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def slugify(text: str) -> str:
    """Lower-case kebab slug: ``"Crumb & Co."`` -> ``"crumb-co"``."""
    folded = _ascii_fold(text).lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def domain_label(company_name: str) -> str:
    """Domain label from a company name: strips trailing LLC/Inc/Corp/Co/Corporation,
    lower-cases and keeps ``[a-z0-9]`` only (``"Crumb Ledger LLC"`` -> ``"crumbledger"``)."""
    tokens = [t for t in re.split(r"[\s,]+", _ascii_fold(company_name).lower()) if t]
    while len(tokens) > 1 and tokens[-1].replace(".", "") in _COMPANY_SUFFIXES:
        tokens.pop()
    return re.sub(r"[^a-z0-9]", "", "".join(tokens))


def new_id(prefix: str) -> str:
    """A new opaque id: ``f"{prefix}_{uuid4().hex[:12]}"``."""
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    """The current time as a timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


def document_sha256(content: str) -> str:
    """SHA-256 hex of the UTF-8 content with ``\\r\\n`` (and lone ``\\r``) normalised to ``\\n`` (ADR-0031)."""
    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _name_key(text: str) -> str:
    cleaned = text.replace(".", "").replace(",", "")
    return " ".join(cleaned.split()).casefold()


def names_match(typed: str, expected: str) -> bool:
    """Typed signature name vs. the founder's name: case-insensitive, whitespace collapsed,
    ``.`` and ``,`` ignored (ADR-0031). ``names_match("alice  chen", "Alice Chen.")`` is True."""
    key = _name_key(typed)
    return bool(key) and key == _name_key(expected)
