"""Cross-cutting HTTP middleware."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx

logger = get_logger("pulse.api.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a correlation id to every request and log a one-line access record.

    Honors an inbound ``X-Request-ID`` (e.g. from a gateway) or mints a new one,
    stores it in a ContextVar for structured logs, and echoes it on the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = rid
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response
