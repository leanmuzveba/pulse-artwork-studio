"""Helper for not-yet-implemented endpoints.

Keeps the intended route surface and OpenAPI document honest while returning a
consistent, machine-readable 501 envelope until the handler is built.
"""

from __future__ import annotations

from app.core.errors import APIError, ErrorCode


def not_implemented(feature: str) -> APIError:
    return APIError(
        code=ErrorCode.NOT_IMPLEMENTED,
        message=f"{feature} is not implemented yet.",
        status_code=501,
    )
