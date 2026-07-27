import math
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.api.experiments import get_experiment_or_404
from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import (
    Artifact,
    Run,
    RunEvent,
    RunLog,
    RunMetric,
    RunParameter,
    RunStatus,
    TrainingTemplate,
)
from runscope_api.run_execution import create_queued_run
from runscope_api.schemas.common import Page
from runscope_api.schemas.runs import (
    ArtifactResponse,
    RunCreate,
    RunEventResponse,
    RunLogResponse,
    RunMetricResponse,
    RunParameterResponse,
    RunResponse,
    TrainingTemplateResponse,
)
from runscope_api.security import CurrentUser, ResearcherUser
from runscope_api.storage import ArtifactStore, get_artifact_store

router = APIRouter(tags=["runs"])


async def get_run_or_404(session: AsyncSession, run_id: UUID) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise AppError("run_not_found", "Run was not found", 404)
    return run


@router.get("/templates", response_model=list[TrainingTemplateResponse])
async def list_templates(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TrainingTemplate]:
    return list(
        (
            await session.scalars(
                select(TrainingTemplate)
                .where(TrainingTemplate.enabled.is_(True))
                .order_by(TrainingTemplate.name, TrainingTemplate.version.desc())
            )
        ).all()
    )


@router.get("/templates/{template_key}", response_model=TrainingTemplateResponse)
async def read_template(
    template_key: str,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    version: str = "1.0.0",
) -> TrainingTemplate:
    template = await session.scalar(
        select(TrainingTemplate).where(
            TrainingTemplate.key == template_key,
            TrainingTemplate.version == version,
            TrainingTemplate.enabled.is_(True),
        )
    )
    if template is None:
        raise AppError("template_not_found", "Training template was not found", 404)
    return template


@router.post("/runs", response_model=RunResponse, status_code=201)
async def create_run(
    body: RunCreate,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    await get_experiment_or_404(session, body.experiment_id)
    return await create_queued_run(session, body, user.id)


@router.get("/runs", response_model=Page[RunResponse])
async def list_runs(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    experiment_id: UUID | None = None,
    status: RunStatus | None = None,
    sort: Literal["created_at", "priority", "status"] = "created_at",
    direction: Literal["asc", "desc"] = "desc",
) -> Page[RunResponse]:
    filters = []
    if experiment_id:
        filters.append(Run.experiment_id == experiment_id)
    if status:
        filters.append(Run.status == status)
    total = await session.scalar(select(func.count(Run.id)).where(*filters)) or 0
    sort_column = {
        "created_at": Run.created_at,
        "priority": Run.priority,
        "status": Run.status,
    }[sort]
    order = asc(sort_column) if direction == "asc" else desc(sort_column)
    items = list(
        (
            await session.scalars(
                select(Run)
                .where(*filters)
                .order_by(order, Run.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return Page(
        items=[RunResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def read_run(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    return await get_run_or_404(session, run_id)


@router.get("/runs/{run_id}/parameters", response_model=list[RunParameterResponse])
async def list_parameters(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RunParameter]:
    await get_run_or_404(session, run_id)
    return list(
        (
            await session.scalars(
                select(RunParameter)
                .where(RunParameter.run_id == run_id)
                .order_by(RunParameter.name)
            )
        ).all()
    )


@router.get("/runs/{run_id}/metrics", response_model=list[RunMetricResponse])
async def list_metrics(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RunMetric]:
    await get_run_or_404(session, run_id)
    return list(
        (
            await session.scalars(
                select(RunMetric).where(RunMetric.run_id == run_id).order_by(RunMetric.recorded_at)
            )
        ).all()
    )


@router.get("/runs/{run_id}/logs", response_model=list[RunLogResponse])
async def list_logs(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RunLog]:
    await get_run_or_404(session, run_id)
    return list(
        (
            await session.scalars(
                select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.sequence_number)
            )
        ).all()
    )


@router.get("/runs/{run_id}/events", response_model=list[RunEventResponse])
async def list_events(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RunEvent]:
    await get_run_or_404(session, run_id)
    return list(
        (
            await session.scalars(
                select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.created_at)
            )
        ).all()
    )


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Artifact]:
    await get_run_or_404(session, run_id)
    return list(
        (
            await session.scalars(
                select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at)
            )
        ).all()
    )


@router.get("/runs/{run_id}/artifacts/{artifact_id}/download")
async def download_artifact(
    run_id: UUID,
    artifact_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    artifact_store: Annotated[ArtifactStore, Depends(get_artifact_store)],
) -> Response:
    artifact = await session.scalar(
        select(Artifact).where(Artifact.id == artifact_id, Artifact.run_id == run_id)
    )
    if artifact is None:
        raise AppError("artifact_not_found", "Artifact was not found", 404)
    try:
        content = await artifact_store.get(artifact.storage_key)
    except FileNotFoundError as exc:
        raise AppError(
            "artifact_content_missing",
            "Artifact metadata exists, but its content is unavailable",
            410,
        ) from exc
    safe_name = artifact.name.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=content,
        media_type=artifact.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
