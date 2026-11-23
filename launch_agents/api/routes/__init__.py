"""The API routers (ADR-0032). Each module exposes ``router = APIRouter()`` and declares its
routes with their full paths (``/api/...``, as in the ADR-0032 table); ``create_app`` includes
them without a prefix. The public routes (``/api/ready``, ``/api/config``, ``/api/agents``)
are T-016's and live here.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import account, admin, auth, billing, cases, jobs, legal, team, website

__all__ = ["ALL_ROUTERS"]

ALL_ROUTERS: tuple[APIRouter, ...] = (
    cases.router,
    jobs.router,
    legal.router,
    website.router,
    auth.router,
    account.router,
    team.router,
    billing.router,
    admin.router,
)
