import math
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import Experiment, Project
from runscope_api.schemas.common import Page
from runscope_api.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from runscope_api.security import CurrentUser, ResearcherUser

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_project_or_404(session: AsyncSession, project_id: UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise AppError("project_not_found", "Project was not found", 404)
    return project


@router.get("", response_model=Page[ProjectResponse])
async def list_projects(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=120)] = None,
    sort: Literal["name", "created_at", "updated_at"] = "created_at",
    direction: Literal["asc", "desc"] = "desc",
) -> Page[ProjectResponse]:
    filters: list[ColumnElement[bool]] = []
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            func.lower(Project.name).like(pattern) | func.lower(Project.description).like(pattern)
        )
    total = await session.scalar(select(func.count(Project.id)).where(*filters)) or 0
    sort_column = {
        "name": Project.name,
        "created_at": Project.created_at,
        "updated_at": Project.updated_at,
    }[sort]
    order = asc(sort_column) if direction == "asc" else desc(sort_column)
    items = list(
        (
            await session.scalars(
                select(Project)
                .where(*filters)
                .order_by(order, Project.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return Page(
        items=[ProjectResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    project = Project(
        name=body.name,
        description=body.description,
        created_by=user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(
    project_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    return await get_project_or_404(session, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    _user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Project:
    project = await get_project_or_404(session, project_id)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(project, name, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    _user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    project = await get_project_or_404(session, project_id)
    experiment_exists = await session.scalar(
        select(Experiment.id).where(Experiment.project_id == project_id).limit(1)
    )
    if experiment_exists is not None:
        raise AppError(
            "project_has_experiments",
            "Delete the project's experiments before deleting the project",
            409,
        )
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)
