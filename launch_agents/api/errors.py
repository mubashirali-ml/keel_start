"""The error envelope (ADR-0017 rules, ADR-0026 codes, ADR-0034 request ids).

Every ``LaunchError`` becomes ``{"error": {"code", "message", "details"}}`` with its
``http_status``; request validation errors become 422 ``invalid_request``; unexpected
exceptions become 500 ``internal`` with a friendly message and the ``request_id`` (never a
stack trace). Unknown ``/api`` paths get a JSON 404; other unknown GET paths fall back to the
SPA's ``index.html`` when the frontend is built.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..config import Settings
from ..domain.errors import LaunchError, RateLimitedError
from ..domain.helpers import new_id

__all__ = [
    "INTERNAL_MESSAGE",
    "REQUEST_ID_HEADER",
    "error_body",
    "install_error_handlers",
    "request_id_for",
]

log = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
INTERNAL_MESSAGE = "Something went wrong on our side. Please try again."
INVALID_REQUEST_MESSAGE = "Some of the details you sent aren't valid. Please check them and try again."
_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_HTTP_CODES = {
    404: ("not_found", "We couldn't find that."),
    405: ("method_not_allowed", "That action isn't available here."),
}


def error_body(code: str, message: str, details: dict[str, Any] | None = None, *, request_id: str | None = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message, "details": dict(details or {})}
    if request_id is not None:
        error["request_id"] = request_id
    return {"error": error}


def request_id_for(request: Request) -> str:
    """The request's id: set by the request middleware, else a valid incoming header, else new."""
    rid = getattr(request.state, "request_id", None)
    if rid:
        return rid
    incoming = request.headers.get(REQUEST_ID_HEADER)
    rid = incoming if incoming and _REQUEST_ID.match(incoming) else new_id("req").replace("_", "-")
    request.state.request_id = rid
    return rid


def _is_api(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


def _spa_response(settings: Settings, path: str) -> Response | None:
    dist = Path(settings.frontend_dist)
    index = dist / "index.html"
    if not index.is_file():
        return None
    root = dist.resolve()
    relative = path.lstrip("/")
    if relative:
        candidate = (dist / relative).resolve()
        if candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
    return FileResponse(index, media_type="text/html")


def install_error_handlers(app: FastAPI, settings: Settings) -> None:
    """Register the envelope handlers and the request-id / 500 middleware on ``app``."""

    @app.exception_handler(LaunchError)
    async def _launch_error(request: Request, exc: LaunchError) -> JSONResponse:
        headers = {REQUEST_ID_HEADER: request_id_for(request)}
        if isinstance(exc, RateLimitedError) and "retry_after_s" in exc.details:
            headers["Retry-After"] = str(int(exc.details["retry_after_s"]))
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.http_status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")), "message": err.get("msg", "")}
            for err in exc.errors()
        ]
        return JSONResponse(
            error_body("invalid_request", INVALID_REQUEST_MESSAGE, {"fields": fields}),
            status_code=422,
            headers={REQUEST_ID_HEADER: request_id_for(request)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404 and request.method in ("GET", "HEAD") and not _is_api(request.url.path):
            spa = _spa_response(settings, request.url.path)
            if spa is not None:
                return spa
        code, message = _HTTP_CODES.get(exc.status_code, ("http_error", "That request couldn't be completed."))
        headers = dict(exc.headers or {})
        headers[REQUEST_ID_HEADER] = request_id_for(request)
        return JSONResponse(error_body(code, message), status_code=exc.status_code, headers=headers)

    @app.middleware("http")
    async def _request_id_and_internal_errors(request: Request, call_next):
        rid = request_id_for(request)
        try:
            response = await call_next(request)
        except Exception:  # unexpected: logged with the request id, never a stack trace in the body
            log.exception("unhandled error in %s %s (request_id=%s)", request.method, request.url.path, rid)
            response = JSONResponse(error_body("internal", INTERNAL_MESSAGE, request_id=rid), status_code=500)
        response.headers.setdefault(REQUEST_ID_HEADER, rid)
        return response
