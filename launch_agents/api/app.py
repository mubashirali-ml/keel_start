"""The FastAPI app factory (ADR-0032). T-001 skeleton; T-016 completes it.

Skeleton: ``GET /api/health``, the error envelope for every ``LaunchError``, CORS, every
router (empty until its ticket merges) and the SPA fallback. When ``services`` is not given
it tries ``build_services(settings)``; while that is still a stub, ``app.state.services`` is
None and only the public skeleton routes work.

    bash scripts/py.sh -m uvicorn launch_agents.api.app:create_app --factory --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..composition import Services, build_services
from ..config import Settings, load_settings
from .errors import install_error_handlers
from .routes import ALL_ROUTERS

__all__ = ["create_app"]

log = logging.getLogger(__name__)


def create_app(services: Services | None = None, settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = services.settings if services is not None else load_settings()
    if services is None:
        try:
            services = build_services(settings)
        except NotImplementedError:
            log.info("build_services is not implemented yet; serving the skeleton app only")
            services = None

    app = FastAPI(
        title=settings.brand_name,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.services = services

    install_error_handlers(app, settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in ALL_ROUTERS:
        app.include_router(router)
    return app
