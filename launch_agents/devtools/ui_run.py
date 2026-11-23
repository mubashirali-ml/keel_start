"""Helpers for browser-driven UI recorded runs (ADR-0005, ADR-0036). Owned by T-011.

Playwright types are imported for annotations only, so this module imports without a browser.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Mapping

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Browser, Page

__all__ = [
    "DEMO_PASSWORD",
    "DEMO_TODAY",
    "RunningApp",
    "assert_no_horizontal_scroll",
    "assert_no_raw_json",
    "build_frontend",
    "capture_matrix",
    "login",
    "running_app",
]

DEMO_TODAY = date(2026, 11, 23)
DEMO_PASSWORD = "demo-password-2026"  # only ever used with fake services


@dataclass
class RunningApp:
    base_url: str
    db_url: str
    case_id: str | None
    users: dict[str, str]  # "alice" -> email, "bob" -> email
    email_drop: Path  # EMAIL_DROP_FILE of the run (ADR-0029)

    def read_emails(self, *, to: str | None = None) -> list[dict]:
        """Parsed JSON lines of the email drop file, oldest first (optionally only to ``to``)."""
        if not self.email_drop.is_file():
            return []
        emails = [json.loads(line) for line in self.email_drop.read_text(encoding="utf-8").splitlines() if line.strip()]
        if to is not None:
            emails = [e for e in emails if str(e.get("to", "")).lower() == to.lower()]
        return emails


@contextmanager
def running_app(
    *,
    seed_stage: str | None = None,
    plan: str = "launch",
    demo_mode: bool = True,
    env: Mapping[str, str] | None = None,
) -> Iterator[RunningApp]:
    """Temp dir + SQLite migrated to head, fake services, seeding before start, uvicorn on a
    free port, waits for ``/api/ready`` (30 s) (ADR-0036, T-011)."""
    raise NotImplementedError("running_app is implemented in T-011")
    yield  # pragma: no cover


def login(page: "Page", app: RunningApp, who: str = "alice") -> None:
    """Log in through the real login form (T-011)."""
    raise NotImplementedError("login is implemented in T-011")


def build_frontend(*, force: bool = False) -> Path:
    """``npm run build`` when ``frontend/dist`` is missing or stale; returns the dist path (T-011)."""
    raise NotImplementedError("build_frontend is implemented in T-011")


def capture_matrix(
    browser: "Browser",
    url: str,
    name: str,
    out_dir: Path,
    *,
    prepare: Callable[["Page"], None] | None = None,
    storage_state: str | None = None,
) -> list[Path]:
    """Desktop/phone x light/dark screenshots ``<name>-<device>-<theme>.png`` (T-011)."""
    raise NotImplementedError("capture_matrix is implemented in T-011")


def assert_no_horizontal_scroll(page: "Page") -> None:
    raise NotImplementedError("assert_no_horizontal_scroll is implemented in T-011")


def assert_no_raw_json(page: "Page") -> None:
    raise NotImplementedError("assert_no_raw_json is implemented in T-011")
