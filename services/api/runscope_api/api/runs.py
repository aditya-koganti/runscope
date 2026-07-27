import math
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from runscope_contracts import EventEnvelope
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.api.experiments import get_experiment_or_404
from runscope_api.config import get_settings
from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.live_events import LiveEventBus, get_live_event_bus
from runscope_api.middleware import correlation_id_context
from runscope_api.models import (
    Artifact,
    OutboxMessage,
    Role,
    Run,
    RunEvent,
    RunLog,
    RunMetric,
    RunParameter,
    RunStatus,
    TrainingTemplate,
)
from runscope_api.run_execution import create_queued_run, validate_parameters
from runscope_api.schemas.common import Page
from runscope_api.schemas.runs import (
    ArtifactResponse,
    RunCompareRequest,
    RunCompareResponse,
    RunComparisonItem,
    RunCreate,
    RunEventResponse,
    RunLogResponse,
    RunMetadataUpdate,
    RunMetricResponse,
    RunParameterResponse,
    RunResponse,
    RunRetryRequest,
    TrainingTemplateResponse,
)
from runscope_api.security import CurrentUser, ResearcherUser
from runscope_api.state_machine import transition_run
from runscope_api.storage import ArtifactStore, get_artifact_store

router = APIRouter(tags=["runs"])


async def get_run_or_404(session: AsyncSession, run_id: UUID) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise AppError("run_not_found", "Run was not found", 404)
    return run


def ensure_run_control(user: object, run: Run) -> None:
    role = getattr(user, "role", None)
    user_id = getattr(user, "id", None)
    if role != Role.ADMINISTRATOR and run.created_by != user_id:
        raise AppError(
            "run_control_denied",
            "Researchers may control only runs they created",
            403,
        )


def add_outbox_event(
    session: AsyncSession,
    run: Run,
    event_type: str,
    payload: dict[str, object],
) -> None:
    event = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id_context.get(),
        run_id=run.id,
        payload=payload,
    )
    session.add(
        OutboxMessage(
            topic=get_settings().broker_topic,
            partition_key=str(run.id),
            envelope=event.model_dump(mode="json"),
        )
    )


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


@router.post("/runs/compare", response_model=RunCompareResponse)
async def compare_runs(
    body: RunCompareRequest,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RunCompareResponse:
    if len(set(body.run_ids)) != len(body.run_ids):
        raise AppError("duplicate_run_ids", "Run IDs must be distinct", 422)
    runs = list((await session.scalars(select(Run).where(Run.id.in_(body.run_ids)))).all())
    if len(runs) != len(body.run_ids):
        raise AppError("run_not_found", "One or more runs were not found", 404)
    if any(run.status != RunStatus.SUCCEEDED for run in runs):
        raise AppError(
            "runs_not_comparable",
            "Only successful runs can be compared",
            409,
        )
    items: list[RunComparisonItem] = []
    for run in sorted(runs, key=lambda item: body.run_ids.index(item.id)):
        parameters = {
            item.name: item.value
            for item in (
                await session.scalars(select(RunParameter).where(RunParameter.run_id == run.id))
            ).all()
        }
        metrics: dict[str, float] = {}
        for metric in (
            await session.scalars(
                select(RunMetric).where(RunMetric.run_id == run.id).order_by(RunMetric.step)
            )
        ).all():
            metrics[metric.name] = metric.value
        items.append(
            RunComparisonItem(
                run=RunResponse.model_validate(run),
                parameters=parameters,
                metrics=metrics,
            )
        )
    metric_names = {name for item in items for name in item.metrics}
    best = {
        name: max(
            (item for item in items if name in item.metrics),
            key=lambda item: item.metrics[name],
        ).run.id
        for name in metric_names
    }
    return RunCompareResponse(items=items, best_by_metric=best)


@router.get("/runs/{run_id}", response_model=RunResponse)
async def read_run(
    run_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    return await get_run_or_404(session, run_id)


@router.post("/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: UUID,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    run = await get_run_or_404(session, run_id)
    ensure_run_control(user, run)
    if run.status != RunStatus.RUNNING:
        raise AppError(
            "run_not_cancellable",
            "Only a running run can be cancelled",
            409,
            {"status": run.status.value},
        )
    transition_run(session, run, RunStatus.CANCELLING, "run.cancel.requested")
    add_outbox_event(
        session,
        run,
        "run.cancel.requested",
        {"requested_by": str(user.id)},
    )
    await session.commit()
    await session.refresh(run)
    return run


@router.post("/runs/{run_id}/retry", response_model=RunResponse, status_code=201)
async def retry_run(
    run_id: UUID,
    body: RunRetryRequest,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    parent = await get_run_or_404(session, run_id)
    ensure_run_control(user, parent)
    if parent.status != RunStatus.FAILED:
        raise AppError(
            "run_not_retryable",
            "Only a failed run can be retried",
            409,
            {"status": parent.status.value},
        )
    template = await session.get(TrainingTemplate, parent.template_id)
    if template is None:
        raise AppError("template_not_found", "Training template was not found", 404)
    parameters = {
        item.name: item.value
        for item in (
            await session.scalars(select(RunParameter).where(RunParameter.run_id == parent.id))
        ).all()
    }
    parameters.update(body.parameter_overrides)
    _, validated_parameters = validate_parameters(template, parameters)
    child = Run(
        experiment_id=parent.experiment_id,
        template_id=parent.template_id,
        status=RunStatus.DRAFT,
        priority=parent.priority,
        requested_cpu=parent.requested_cpu,
        requested_memory_mb=parent.requested_memory_mb,
        attempt_number=parent.attempt_number + 1,
        parent_run_id=parent.id,
        created_by=user.id,
        notes=parent.notes,
        tags=parent.tags,
    )
    session.add(child)
    await session.flush()
    session.add_all(
        RunParameter(run_id=child.id, name=name, value=value)
        for name, value in validated_parameters.items()
    )
    transition_run(
        session,
        child,
        RunStatus.QUEUED,
        "run.queued",
        {"retry_of": str(parent.id)},
    )
    add_outbox_event(
        session,
        child,
        "run.submitted",
        {
            "template_key": template.key,
            "template_version": template.version,
            "retry_of": str(parent.id),
            "attempt_number": child.attempt_number,
        },
    )
    await session.commit()
    await session.refresh(child)
    return child


@router.patch("/runs/{run_id}/metadata", response_model=RunResponse)
async def update_run_metadata(
    run_id: UUID,
    body: RunMetadataUpdate,
    user: ResearcherUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Run:
    run = await get_run_or_404(session, run_id)
    ensure_run_control(user, run)
    run.notes = body.notes
    normalized = [tag.strip().lower() for tag in body.tags if tag.strip()]
    if any(len(tag) > 40 for tag in normalized):
        raise AppError("invalid_tags", "Tags must be at most 40 characters", 422)
    run.tags = list(dict.fromkeys(normalized))
    session.add(
        RunEvent(
            run_id=run.id,
            event_type="run.metadata.updated",
            event_metadata={"updated_by": str(user.id)},
        )
    )
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/runs/{run_id}/stream", response_class=StreamingResponse)
async def stream_run(
    run_id: UUID,
    request: Request,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    live_bus: Annotated[LiveEventBus, Depends(get_live_event_bus)],
) -> StreamingResponse:
    await get_run_or_404(session, run_id)

    async def events() -> AsyncIterator[str]:
        yield "retry: 2000\n\n"
        async for event in live_bus.subscribe(run_id):
            if await request.is_disconnected():
                break
            yield (
                f"id: {event.event_id}\n"
                f"event: {event.event_type}\n"
                f"data: {event.model_dump_json()}\n\n"
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
