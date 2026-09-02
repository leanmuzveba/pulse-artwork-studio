"""Shared response envelope schemas (documented in the OpenAPI spec)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None


class SuccessResponse(BaseModel, Generic[T]):
    data: T
    request_id: str | None = None


class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    environment: str
