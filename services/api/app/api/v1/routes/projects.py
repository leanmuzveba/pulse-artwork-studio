"""Projects — CRUD over a user's artwork projects."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, load_owned_project
from app.core.logging import request_id_ctx
from app.db.enums import ProjectStatus
from app.db.models import Project, User
from app.db.session import get_session
from app.schemas.common import SuccessResponse
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.post(
    "",
    response_model=SuccessResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProjectResponse]:
    project = Project(owner_id=user.id, name=payload.name)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return SuccessResponse(
        data=ProjectResponse.model_validate(project), request_id=request_id_ctx.get()
    )


@router.get(
    "",
    response_model=SuccessResponse[list[ProjectResponse]],
    summary="List the current user's projects",
)
async def list_projects(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[ProjectResponse]]:
    result = await session.scalars(
        select(Project)
        .where(Project.owner_id == user.id, Project.status != ProjectStatus.DELETED)
        .order_by(Project.created_at.desc())
    )
    projects = [ProjectResponse.model_validate(p) for p in result.all()]
    return SuccessResponse(data=projects, request_id=request_id_ctx.get())


@router.get(
    "/{project_id}",
    response_model=SuccessResponse[ProjectResponse],
    summary="Get a project",
)
async def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ProjectResponse]:
    project = await load_owned_project(session, user, project_id)
    return SuccessResponse(
        data=ProjectResponse.model_validate(project), request_id=request_id_ctx.get()
    )
