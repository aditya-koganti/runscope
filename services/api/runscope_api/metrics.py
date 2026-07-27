import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from runscope_api.models import OutboxMessage, Run, RunStatus, Worker, WorkerStatus

HTTP_REQUESTS = Counter(
    "runscope_http_requests_total",
    "HTTP requests handled by the API.",
    ("method", "path", "status"),
)
HTTP_DURATION = Histogram(
    "runscope_http_request_duration_seconds",
    "API request duration in seconds.",
    ("method", "path"),
)
RUNS_BY_STATUS = Gauge(
    "runscope_runs",
    "Durable runs by lifecycle status.",
    ("status",),
)
QUEUE_DEPTH = Gauge("runscope_queue_depth", "Runs currently waiting for scheduling.")
WORKERS_ONLINE = Gauge("runscope_workers_online", "Workers with a fresh online status.")
WORKER_CPU_AVAILABLE = Gauge(
    "runscope_worker_cpu_available",
    "Allocatable worker CPU currently available.",
)
OUTBOX_BACKLOG = Gauge(
    "runscope_outbox_backlog",
    "Unpublished messages still eligible for dispatch.",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        HTTP_DURATION.labels(request.method, path).observe(time.perf_counter() - started)
        return response


async def refresh_domain_metrics(session: AsyncSession, max_outbox_attempts: int) -> None:
    rows = (
        await session.execute(select(Run.status, func.count(Run.id)).group_by(Run.status))
    ).all()
    counts: dict[RunStatus, int] = {status: int(count) for status, count in rows}
    for status in RunStatus:
        RUNS_BY_STATUS.labels(status.value).set(counts.get(status, 0))
    QUEUE_DEPTH.set(counts.get(RunStatus.QUEUED, 0))
    WORKERS_ONLINE.set(
        await session.scalar(
            select(func.count(Worker.id)).where(Worker.status == WorkerStatus.ONLINE)
        )
        or 0
    )
    WORKER_CPU_AVAILABLE.set(
        await session.scalar(
            select(func.coalesce(func.sum(Worker.available_cpu), 0.0)).where(
                Worker.status == WorkerStatus.ONLINE
            )
        )
        or 0
    )
    OUTBOX_BACKLOG.set(
        await session.scalar(
            select(func.count(OutboxMessage.id)).where(
                OutboxMessage.published_at.is_(None),
                OutboxMessage.publish_attempts < max_outbox_attempts,
            )
        )
        or 0
    )
