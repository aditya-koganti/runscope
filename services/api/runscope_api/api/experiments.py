import math
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import String, asc, cast, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from runscope_api.api.projects import get_project_or_404
from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import Experiment
from runscope_api.schemas.common import Page
from runscope_api.schemas.projects import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
)
from runscope_api.security import CurrentUser, ResearcherUser

router = APIRouter(prefix="/experiments", tags=["experiments"])


async def get_experiment_or_404(session: AsyncSession, experiment_id: UUID) -> Experiment:
    experiment = await session.get(Experiment, experiment_id)
    if experiment is None:
        raise AppError("experiment_not_found", "Experiment was not found", 404)
    return experiment


async def ensure_unique_name(
    session: AsyncSession,
    project_id: UUID,
    name: str,
    exclude_id: UUID | None = None,
) -> None:
    query = select(Experiment.id).where(
        Experiment.project_id == project_id,
        func.lower(Experiment.name) == name.lower(),
    )
    if exclude_id:
        query = query.where(Experiment.id != exclude_id)
    if await session.scalar(query.limit(1)) is not None:
        raise AppError(
            "experiment_name_conflict",
            "An experiment with this name already exists in the project",
            409,
        )


@router.get("", response_model=Page[ExperimentResponse])
async def list_experiments(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=120)] = None,
    project_id: UUID | None = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    sort: Literal["name", "created_at", "updated_at"] = "created_at",
    direction: Literal["asc", "desc"] = "desc",
) -> Page[ExperimentResponse]:
    filters: list[ColumnElement[bool]] = []
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            func.lower(Experiment.name).like(pattern)
            | func.lower(Experiment.description).like(pattern)
        )
    if project_id:
        filters.append(Experiment.project_id == project_id)
    if tag:
        filters.append(cast(Experiment.tags, String).like(f'%"{tag.strip().lower()}"%'))
    total = await session.scalar(select(func.count(Experiment.id)).where(*filters)) or 0
    sort_column = {
        "name": Experiment.name,
        "created_at": Experiment.created_at,
        "updated_at": Experiment.updated_at,
    }[sort]
    order = asc(sort_column) if direction == "asc" else desc(sort_column)
    items = list(
        (
            await session.scalars(
                select(Experiment)
                .where(*filters)
                .order_by(order, Experiment.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return Page(
        items=[ExperimentResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    body: ExperimentCreate,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Experiment:
    await get_project_or_404(session, body.project_id)
    await ensure_unique_name(session, body.project_id, body.name)
    experiment = Experiment(
        project_id=body.project_id,
        name=body.name,
        description=body.description,
        tags=body.tags,
        created_by=user.id,
    )
    session.add(experiment)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "experiment_name_conflict",
            "An experiment with this name already exists in the project",
            409,
        ) from exc
    await session.refresh(experiment)
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def read_experiment(
    experiment_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Experiment:
    return await get_experiment_or_404(session, experiment_id)


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: UUID,
    body: ExperimentUpdate,
    _user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Experiment:
    experiment = await get_experiment_or_404(session, experiment_id)
    values = body.model_dump(exclude_unset=True)
    if name := values.get("name"):
        await ensure_unique_name(
            session,
            experiment.project_id,
            name,
            exclude_id=experiment.id,
        )
    for name, value in values.items():
        setattr(experiment, name, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "experiment_name_conflict",
            "An experiment with this name already exists in the project",
            409,
        ) from exc
    await session.refresh(experiment)
    return experiment


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: UUID,
    _user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    experiment = await get_experiment_or_404(session, experiment_id)
    await session.delete(experiment)
    await session.commit()
    return Response(status_code=204)
