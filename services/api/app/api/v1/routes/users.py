"""Users — profile of the authenticated account."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.logging import request_id_ctx
from app.db.models import User
from app.schemas.auth import UserResponse
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get the authenticated user's profile",
)
async def get_me(user: User = Depends(get_current_user)) -> SuccessResponse[UserResponse]:
    return SuccessResponse(
        data=UserResponse.model_validate(user), request_id=request_id_ctx.get()
    )
