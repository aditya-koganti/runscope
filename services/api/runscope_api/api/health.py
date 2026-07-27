import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

import boto3
from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.broker import KafkaBroker
from runscope_api.config import Settings, get_settings
from runscope_api.db import SessionFactory, get_session
from runscope_api.metrics import refresh_domain_metrics
from runscope_api.models import OutboxMessage, Run, RunStatus, Worker, WorkerStatus
from runscope_api.security import CurrentUser

router = APIRouter(tags=["platform"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class DependencyStatus(BaseModel):
    status: Literal["healthy", "unavailable"]
    latency_ms: float


class DependencyHealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    dependencies: dict[str, DependencyStatus]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, str]


class PlatformSummaryResponse(BaseModel):
    active_runs: int
    queued_runs: int
    failed_runs: int
    successful_runs: int
    success_rate: float
    average_duration_seconds: float | None
    workers_online: int
    workers_total: int
    available_cpu: float
    total_cpu: float
    available_memory_mb: int
    total_memory_mb: int
    queue_depth: int
    unpublished_messages: int


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


async def timed_probe(probe: Callable[[], Awaitable[None]]) -> DependencyStatus:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(2):
            await probe()
        status: Literal["healthy", "unavailable"] = "healthy"
    except Exception:
        status = "unavailable"
    return DependencyStatus(
        status=status,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


async def probe_postgresql() -> None:
    async with SessionFactory() as session:
        await session.execute(text("SELECT 1"))


async def probe_redis(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def probe_redpanda(settings: Settings) -> None:
    broker = KafkaBroker(settings.broker_bootstrap_servers)
    try:
        await broker.start()
    finally:
        await broker.stop()


async def probe_minio(settings: Settings) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )
    await asyncio.to_thread(client.list_buckets)


async def probe_scheduler(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url)
    try:
        if await client.get("runscope:scheduler:heartbeat") is None:
            raise RuntimeError("Scheduler heartbeat is absent")
    finally:
        await client.aclose()


async def dependency_statuses(settings: Settings) -> dict[str, DependencyStatus]:
    names = ("postgresql", "redis", "redpanda", "minio", "scheduler")
    results = await asyncio.gather(
        timed_probe(probe_postgresql),
        timed_probe(lambda: probe_redis(settings)),
        timed_probe(lambda: probe_redpanda(settings)),
        timed_probe(lambda: probe_minio(settings)),
        timed_probe(lambda: probe_scheduler(settings)),
    )
    return {
        "api": DependencyStatus(status="healthy", latency_ms=0),
        **dict(zip(names, results, strict=True)),
    }


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(response: Response) -> ReadinessResponse:
    statuses = await dependency_statuses(get_settings())
    required = ("postgresql", "redis", "redpanda", "minio")
    ready = all(statuses[name].status == "healthy" for name in required)
    if not ready:
        response.status_code = 503
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        dependencies={name: item.status for name, item in statuses.items()},
    )


@router.get("/platform/dependencies", response_model=DependencyHealthResponse)
async def dependency_health(_user: CurrentUser) -> DependencyHealthResponse:
    dependencies = await dependency_statuses(get_settings())
    overall = (
        "healthy" if all(item.status == "healthy" for item in dependencies.values()) else "degraded"
    )
    return DependencyHealthResponse(status=overall, dependencies=dependencies)


@router.get("/platform/summary", response_model=PlatformSummaryResponse)
async def platform_summary(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlatformSummaryResponse:
    runs = list((await session.scalars(select(Run))).all())
    terminal = [
        run
        for run in runs
        if run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}
    ]
    successful = sum(run.status == RunStatus.SUCCEEDED for run in runs)
    durations = [
        (run.completed_at - run.started_at).total_seconds()
        for run in runs
        if run.started_at is not None and run.completed_at is not None
    ]
    worker_totals = (
        await session.execute(
            select(
                func.count(Worker.id),
                func.coalesce(func.sum(Worker.total_cpu), 0.0),
                func.coalesce(func.sum(Worker.available_cpu), 0.0),
                func.coalesce(func.sum(Worker.total_memory_mb), 0),
                func.coalesce(func.sum(Worker.available_memory_mb), 0),
            ).where(Worker.status == WorkerStatus.ONLINE)
        )
    ).one()
    queued = sum(run.status == RunStatus.QUEUED for run in runs)
    return PlatformSummaryResponse(
        active_runs=sum(
            run.status in {RunStatus.SCHEDULING, RunStatus.RUNNING, RunStatus.CANCELLING}
            for run in runs
        ),
        queued_runs=queued,
        failed_runs=sum(run.status == RunStatus.FAILED for run in runs),
        successful_runs=successful,
        success_rate=successful / len(terminal) if terminal else 0,
        average_duration_seconds=sum(durations) / len(durations) if durations else None,
        workers_online=int(worker_totals[0]),
        workers_total=await session.scalar(select(func.count(Worker.id))) or 0,
        available_cpu=float(worker_totals[2]),
        total_cpu=float(worker_totals[1]),
        available_memory_mb=int(worker_totals[4]),
        total_memory_mb=int(worker_totals[3]),
        queue_depth=queued,
        unpublished_messages=await session.scalar(
            select(func.count(OutboxMessage.id)).where(OutboxMessage.published_at.is_(None))
        )
        or 0,
    )


@router.get("/metrics")
async def prometheus_metrics(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    settings = get_settings()
    await refresh_domain_metrics(session, settings.outbox_max_attempts)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
