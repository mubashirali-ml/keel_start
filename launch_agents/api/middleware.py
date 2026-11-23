"""Middleware stack in ADR-0032 order: request id + structured logging (T-033), security headers
and CSRF (T-032), CORS, the 100 s chat timeout (ADR-0023). Owned by T-016."""

from __future__ import annotations

from fastapi import FastAPI

from ..config import Settings

__all__ = ["install_middleware"]


def install_middleware(app: FastAPI, settings: Settings) -> None:
    """Install the ADR-0032 middleware stack on ``app`` (T-016)."""
    raise NotImplementedError("install_middleware is implemented in T-016")
