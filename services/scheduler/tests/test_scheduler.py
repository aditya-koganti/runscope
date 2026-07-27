from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from runscope_api.config import Settings
from runscope_api.db import SessionFactory
from runscope_api.models import (
    Experiment,
    Project,
    ResourceAllocation,
    Role,
    Run,
    RunStatus,
    TrainingTemplate,
    User,
    Worker,
    WorkerStatus,
)
from runscope_api.security import hash_password
from runscope_api.seed import seed_training_templates
from runscope_api.worker_registry import register_worker
from runscope_scheduler.service import recover_expired_allocations, schedule_once
from sqlalchemy import select


def scheduler_settings() -> Settings:
    return Settings(
        outbox_dispatcher_enabled=False,
        worker_stale_seconds=15,
        allocation_lease_seconds=30,
    )


async def seed_run(
    *,
    priority: int = 0,
    cpu: float = 1,
    memory_mb: int = 512,
) -> UUID:
    async with SessionFactory() as session:
        user = User(
            email=f"scheduler-{uuid4()}@runscope.dev",
            password_hash=hash_password("SchedulerDemo123!"),
            role=Role.RESEARCHER,
        )
        session.add(user)
        await session.flush()
        project = Project(name=f"Scheduler {uuid4()}", description="", created_by=user.id)
        session.add(project)
        await session.flush()
        experiment = Experiment(
            project_id=project.id,
            name="Capacity",
            description="",
            tags=[],
            created_by=user.id,
        )
        session.add(experiment)
        await session.commit()
        await seed_training_templates(session)
        template = await session.scalar(
            select(TrainingTemplate).where(TrainingTemplate.key == "slow-demonstration")
        )
        assert template is not None
        run = Run(
            experiment_id=experiment.id,
            template_id=template.id,
            status=RunStatus.QUEUED,
            priority=priority,
            requested_cpu=cpu,
            requested_memory_mb=memory_mb,
            created_by=user.id,
        )
        session.add(run)
        await session.commit()
        return run.id


@pytest.mark.asyncio
async def test_scheduler_assigns_compatible_worker_and_is_idempotent() -> None:
    run_id = await seed_run()
    async with SessionFactory() as session:
        worker = await register_worker(session, "scheduler-worker", 2, 2048)
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 1
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 0
        run = await session.get(Run, run_id)
        allocation = await session.scalar(
            select(ResourceAllocation).where(ResourceAllocation.run_id == run_id)
        )
        persisted_worker = await session.get(Worker, worker.id)
        assert run is not None and run.status == RunStatus.SCHEDULING
        assert run.assigned_worker_id == worker.id
        assert allocation is not None and allocation.released_at is None
        assert persisted_worker is not None
        assert persisted_worker.available_cpu == 1
        assert persisted_worker.available_memory_mb == 1536
        assert persisted_worker.current_run_count == 1


@pytest.mark.asyncio
async def test_scheduler_leaves_run_queued_when_capacity_is_insufficient() -> None:
    run_id = await seed_run(cpu=2, memory_mb=2048)
    async with SessionFactory() as session:
        await register_worker(session, "small-worker", 1, 1024)
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 0
        run = await session.get(Run, run_id)
        assert run is not None and run.status == RunStatus.QUEUED


@pytest.mark.asyncio
async def test_scheduler_respects_priority_under_constrained_capacity() -> None:
    low_id = await seed_run(priority=0)
    high_id = await seed_run(priority=10)
    async with SessionFactory() as session:
        await register_worker(session, "one-slot-worker", 1, 512)
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 1
        low = await session.get(Run, low_id)
        high = await session.get(Run, high_id)
        assert low is not None and low.status == RunStatus.QUEUED
        assert high is not None and high.status == RunStatus.SCHEDULING


@pytest.mark.asyncio
async def test_expired_lease_is_released_and_run_is_requeued() -> None:
    run_id = await seed_run()
    async with SessionFactory() as session:
        worker = await register_worker(session, "expiry-worker", 1, 512)
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 1
        allocation = await session.scalar(
            select(ResourceAllocation).where(ResourceAllocation.run_id == run_id)
        )
        assert allocation is not None
        allocation.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    async with SessionFactory() as session:
        assert await recover_expired_allocations(session, scheduler_settings()) == 1
        await session.commit()
        run = await session.get(Run, run_id)
        persisted_worker = await session.get(Worker, worker.id)
        assert run is not None and run.status == RunStatus.QUEUED
        assert run.assigned_worker_id is None
        assert persisted_worker is not None and persisted_worker.available_cpu == 1


@pytest.mark.asyncio
async def test_stale_worker_recovery_releases_assignment() -> None:
    run_id = await seed_run()
    async with SessionFactory() as session:
        worker = await register_worker(session, "stale-worker", 1, 512)
    async with SessionFactory() as session:
        assert await schedule_once(session, scheduler_settings()) == 1
        persisted_worker = await session.get(Worker, worker.id)
        assert persisted_worker is not None
        persisted_worker.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
    async with SessionFactory() as session:
        assert await recover_expired_allocations(session, scheduler_settings()) == 1
        await session.commit()
        run = await session.get(Run, run_id)
        persisted_worker = await session.get(Worker, worker.id)
        assert run is not None and run.status == RunStatus.QUEUED
        assert persisted_worker is not None
        assert persisted_worker.status == WorkerStatus.STALE
