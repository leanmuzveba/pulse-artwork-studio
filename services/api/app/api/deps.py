"""Shared FastAPI dependencies (auth, current user)."""

from __future__ import annotations

import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError, ErrorCode
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.db.enums import UserStatus
from app.db.models import User
from app.db.session import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from a Bearer access token."""
    unauthorized = APIError(
        ErrorCode.UNAUTHORIZED, "Authentication required.", status_code=401
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise APIError(
            ErrorCode.UNAUTHORIZED, "Invalid or expired token.", status_code=401
        ) from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise APIError(ErrorCode.UNAUTHORIZED, "Invalid token type.", status_code=401)

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise unauthorized from exc

    user = await session.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise APIError(
            ErrorCode.UNAUTHORIZED, "User not found or inactive.", status_code=401
        )
    return user
