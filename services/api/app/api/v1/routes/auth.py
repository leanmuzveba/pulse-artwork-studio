"""Authentication — register, login, refresh."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError, ErrorCode
from app.core.logging import request_id_ctx
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.enums import PlanTier
from app.db.models import AuditLog, Entitlement, User
from app.db.session import get_session
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> SuccessResponse[UserResponse]:
    email = payload.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise APIError(
            ErrorCode.CONFLICT,
            "An account with this email already exists.",
            status_code=409,
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    user.entitlement = Entitlement(plan=PlanTier.FREE)
    session.add(user)
    await session.flush()
    session.add(
        AuditLog(
            user_id=user.id,
            action="user.register",
            entity_type="user",
            entity_id=str(user.id),
        )
    )
    await session.commit()
    await session.refresh(user)
    return SuccessResponse(
        data=UserResponse.model_validate(user), request_id=request_id_ctx.get()
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Log in and receive access + refresh tokens",
)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> SuccessResponse[TokenResponse]:
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    # Verify even when the user is missing to avoid leaking which emails exist.
    valid = user is not None and verify_password(payload.password, user.hashed_password)
    if not valid or user is None:
        raise APIError(
            ErrorCode.UNAUTHORIZED, "Incorrect email or password.", status_code=401
        )

    tokens = TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
    session.add(AuditLog(user_id=user.id, action="user.login", entity_type="user"))
    await session.commit()
    return SuccessResponse(data=tokens, request_id=request_id_ctx.get())


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Exchange a refresh token for a new access + refresh pair",
)
async def refresh(payload: RefreshRequest) -> SuccessResponse[TokenResponse]:
    try:
        claims = decode_token(payload.refresh_token)
    except jwt.PyJWTError as exc:
        raise APIError(
            ErrorCode.UNAUTHORIZED, "Invalid or expired refresh token.", status_code=401
        ) from exc

    if claims.get("type") != TOKEN_TYPE_REFRESH:
        raise APIError(ErrorCode.UNAUTHORIZED, "Invalid token type.", status_code=401)

    subject = claims.get("sub")
    tokens = TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )
    return SuccessResponse(data=tokens, request_id=request_id_ctx.get())
