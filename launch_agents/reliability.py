"""Timeouts, retries and budgets shared by every adapter and provider (ADR-0023). Pure; T-001."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

import httpx

from .domain.errors import LaunchError, RetryableError

__all__ = ["Deadline", "RetryPolicy", "RetryableError", "call_with_retry", "is_transient", "retry_delay"]

T = TypeVar("T")

_TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _status_of(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    for attr in ("status_code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def is_transient(exc: BaseException) -> bool:
    """True for errors worth retrying: httpx timeouts / connect / network errors, HTTP 408, 425,
    429 and 5xx responses, ``TimeoutError`` / ``ConnectionError`` and ``RetryableError``.

    Other ``LaunchError``s are deliberate, founder-facing answers and never retried.
    """
    if isinstance(exc, RetryableError):
        return True
    if isinstance(exc, LaunchError):
        return False
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = _status_of(exc)
    return status is not None and (status in _TRANSIENT_STATUS or 500 <= status <= 599)


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3  # total tries, including the first
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter: bool = True  # +-20 %, disabled in tests
    retry_on: Callable[[BaseException], bool] = is_transient


def _retry_after(exc: BaseException) -> float | None:
    """Seconds from a ``Retry-After`` header (HTTP 429/503) or ``details.retry_after_s``."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None and _status_of(exc) in (429, 503):
        value = headers.get("Retry-After") if hasattr(headers, "get") else None
        if value is not None:
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                return None
    if isinstance(exc, LaunchError):
        value = exc.details.get("retry_after_s")
        if isinstance(value, (int, float)):
            return max(0.0, float(value))
    return None


def retry_delay(policy: RetryPolicy, retry_number: int, exc: BaseException | None = None) -> float:
    """Delay before retry ``retry_number`` (1 = the first retry): ``base * 2**(n-1)`` capped at
    ``max_delay_s``, +-20 % jitter when enabled; a shorter ``Retry-After`` is honoured."""
    if exc is not None:
        hinted = _retry_after(exc)
        if hinted is not None and hinted < policy.max_delay_s:
            return hinted
    delay = min(policy.base_delay_s * (2 ** (retry_number - 1)), policy.max_delay_s)
    if policy.jitter:
        delay *= random.uniform(0.8, 1.2)
    return delay


def call_with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Call ``fn`` up to ``policy.attempts`` times, retrying only when ``policy.retry_on(exc)``.

    The last error is re-raised unchanged. ``on_retry(attempt, exc)`` is called before each
    sleep with the number of the attempt that failed. Tests pass a no-op ``sleep``.
    """
    attempts = max(1, policy.attempts)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt >= attempts or not policy.retry_on(exc):
                raise
            if on_retry is not None:
                on_retry(attempt, exc)
            sleep(retry_delay(policy, attempt, exc))
    raise AssertionError("unreachable")  # pragma: no cover


class Deadline:
    """An overall time budget across several calls."""

    def __init__(self, seconds: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.seconds = float(seconds)
        self._clock = clock
        self._start = clock()

    def remaining(self) -> float:
        return max(0.0, self.seconds - (self._clock() - self._start))

    def expired(self) -> bool:
        return self.remaining() <= 0.0
