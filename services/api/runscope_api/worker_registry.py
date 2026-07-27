from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.models import ResourceAllocation, Worker, WorkerStatus


async def register_worker(
    session: AsyncSession,
    name: str,
    total_cpu: float,
    total_memory_mb: int,
) -> Worker:
    worker = await session.scalar(select(Worker).where(Worker.name == name).with_for_update())
    now = datetime.now(UTC)
    if worker is None:
        worker = Worker(
            name=name,
            status=WorkerStatus.ONLINE,
            total_cpu=total_cpu,
            available_cpu=total_cpu,
            total_memory_mb=total_memory_mb,
            available_memory_mb=total_memory_mb,
            current_run_count=0,
            last_heartbeat_at=now,
        )
        session.add(worker)
        await session.flush()
    else:
        worker.status = WorkerStatus.ONLINE
        worker.total_cpu = total_cpu
        worker.total_memory_mb = total_memory_mb
        worker.last_heartbeat_at = now
        await refresh_worker_capacity(session, worker)
    await session.commit()
    await session.refresh(worker)
    return worker


async def refresh_worker_capacity(session: AsyncSession, worker: Worker) -> None:
    active_cpu, active_memory, active_count = (
        await session.execute(
            select(
                func.coalesce(func.sum(ResourceAllocation.cpu), 0.0),
                func.coalesce(func.sum(ResourceAllocation.memory_mb), 0),
                func.count(ResourceAllocation.id),
            ).where(
                ResourceAllocation.worker_id == worker.id,
                ResourceAllocation.released_at.is_(None),
            )
        )
    ).one()
    worker.available_cpu = max(0.0, worker.total_cpu - float(active_cpu))
    worker.available_memory_mb = max(0, worker.total_memory_mb - int(active_memory))
    worker.current_run_count = int(active_count)


async def heartbeat_worker(
    session: AsyncSession,
    worker_id: UUID,
    lease_seconds: int,
) -> Worker | None:
    worker = await session.get(Worker, worker_id)
    if worker is None:
        return None
    now = datetime.now(UTC)
    worker.status = WorkerStatus.ONLINE
    worker.last_heartbeat_at = now
    allocations = (
        await session.scalars(
            select(ResourceAllocation).where(
                ResourceAllocation.worker_id == worker.id,
                ResourceAllocation.released_at.is_(None),
            )
        )
    ).all()
    for allocation in allocations:
        allocation.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await refresh_worker_capacity(session, worker)
    await session.commit()
    await session.refresh(worker)
    return worker


async def release_allocation(session: AsyncSession, run_id: UUID) -> ResourceAllocation | None:
    allocation = await session.scalar(
        select(ResourceAllocation)
        .where(
            ResourceAllocation.run_id == run_id,
            ResourceAllocation.released_at.is_(None),
        )
        .with_for_update()
    )
    if allocation is None:
        return None
    allocation.released_at = datetime.now(UTC)
    await session.flush()
    worker = await session.get(Worker, allocation.worker_id)
    if worker is not None:
        await refresh_worker_capacity(session, worker)
    return allocation
