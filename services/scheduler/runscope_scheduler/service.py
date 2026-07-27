from datetime import UTC, datetime, timedelta
from uuid import uuid4

from runscope_api.config import Settings
from runscope_api.models import (
    OutboxMessage,
    ResourceAllocation,
    Run,
    RunStatus,
    Worker,
    WorkerStatus,
)
from runscope_api.state_machine import transition_run
from runscope_api.worker_registry import refresh_worker_capacity, release_allocation
from runscope_contracts import EventEnvelope
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def add_assignment_event(
    session: AsyncSession,
    settings: Settings,
    run: Run,
    worker: Worker,
    allocation: ResourceAllocation,
) -> None:
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="run.assigned",
        occurred_at=datetime.now(UTC),
        correlation_id=f"scheduler-{uuid4()}",
        run_id=run.id,
        worker_id=worker.id,
        payload={
            "lease_token": str(allocation.lease_token),
            "requested_cpu": allocation.cpu,
            "requested_memory_mb": allocation.memory_mb,
        },
    )
    session.add(
        OutboxMessage(
            topic=settings.broker_topic,
            partition_key=str(run.id),
            envelope=event.model_dump(mode="json"),
        )
    )


async def recover_expired_allocations(
    session: AsyncSession,
    settings: Settings,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(UTC)
    stale_before = current_time - timedelta(seconds=settings.worker_stale_seconds)
    stale_workers = list(
        (
            await session.scalars(
                select(Worker)
                .where(
                    Worker.status == WorkerStatus.ONLINE,
                    Worker.last_heartbeat_at < stale_before,
                )
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    stale_ids = {worker.id for worker in stale_workers}
    for worker in stale_workers:
        worker.status = WorkerStatus.STALE

    condition = ResourceAllocation.lease_expires_at < current_time
    if stale_ids:
        condition = or_(condition, ResourceAllocation.worker_id.in_(stale_ids))
    allocations = list(
        (
            await session.scalars(
                select(ResourceAllocation)
                .where(
                    ResourceAllocation.released_at.is_(None),
                    condition,
                )
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for allocation in allocations:
        run = await session.get(Run, allocation.run_id)
        if run is not None:
            if run.status == RunStatus.SCHEDULING:
                transition_run(
                    session,
                    run,
                    RunStatus.QUEUED,
                    "run.assignment.expired",
                    {"worker_id": str(allocation.worker_id)},
                )
                run.assigned_worker_id = None
            elif run.status == RunStatus.RUNNING:
                run.failure_code = "worker_lease_expired"
                run.failure_message = "The assigned worker stopped heartbeating"
                transition_run(
                    session,
                    run,
                    RunStatus.FAILED,
                    "run.failed",
                    {"worker_id": str(allocation.worker_id), "reason": "lease_expired"},
                )
            elif run.status == RunStatus.CANCELLING:
                transition_run(
                    session,
                    run,
                    RunStatus.CANCELLED,
                    "run.cancelled",
                    {"worker_id": str(allocation.worker_id), "reason": "lease_expired"},
                )
        await release_allocation(session, allocation.run_id)
    for worker in stale_workers:
        await refresh_worker_capacity(session, worker)
    return len(allocations)


async def schedule_once(session: AsyncSession, settings: Settings) -> int:
    await recover_expired_allocations(session, settings)
    now = datetime.now(UTC)
    healthy_after = now - timedelta(seconds=settings.worker_stale_seconds)
    queued_runs = list(
        (
            await session.scalars(
                select(Run)
                .where(Run.status == RunStatus.QUEUED)
                .order_by(Run.priority.desc(), Run.created_at.asc(), Run.id.asc())
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    assigned = 0
    for run in queued_runs:
        worker = await session.scalar(
            select(Worker)
            .where(
                Worker.status == WorkerStatus.ONLINE,
                Worker.last_heartbeat_at >= healthy_after,
                Worker.available_cpu >= run.requested_cpu,
                Worker.available_memory_mb >= run.requested_memory_mb,
            )
            .order_by(Worker.current_run_count.asc(), Worker.name.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if worker is None:
            continue
        allocation = ResourceAllocation(
            run_id=run.id,
            worker_id=worker.id,
            cpu=run.requested_cpu,
            memory_mb=run.requested_memory_mb,
            lease_expires_at=now + timedelta(seconds=settings.allocation_lease_seconds),
        )
        session.add(allocation)
        await session.flush()
        run.assigned_worker_id = worker.id
        transition_run(
            session,
            run,
            RunStatus.SCHEDULING,
            "run.scheduling",
            {"worker_id": str(worker.id), "lease_id": str(allocation.id)},
        )
        worker.available_cpu -= run.requested_cpu
        worker.available_memory_mb -= run.requested_memory_mb
        worker.current_run_count += 1
        add_assignment_event(session, settings, run, worker, allocation)
        assigned += 1
    await session.commit()
    return assigned
