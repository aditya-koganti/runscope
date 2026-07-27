from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.config import get_settings
from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import ResourceAllocation, Worker
from runscope_api.schemas.workers import (
    ResourceAllocationResponse,
    WorkerDetailResponse,
    WorkerRegister,
    WorkerResponse,
)
from runscope_api.security import AdministratorUser, CurrentUser
from runscope_api.worker_registry import heartbeat_worker, register_worker

router = APIRouter(prefix="/workers", tags=["workers"])


async def get_worker_or_404(session: AsyncSession, worker_id: UUID) -> Worker:
    worker = await session.get(Worker, worker_id)
    if worker is None:
        raise AppError("worker_not_found", "Worker was not found", 404)
    return worker


@router.get("", response_model=list[WorkerResponse])
async def list_workers(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Worker]:
    return list((await session.scalars(select(Worker).order_by(Worker.status, Worker.name))).all())


@router.get("/{worker_id}", response_model=WorkerDetailResponse)
async def read_worker(
    worker_id: UUID,
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkerDetailResponse:
    worker = await get_worker_or_404(session, worker_id)
    allocations = list(
        (
            await session.scalars(
                select(ResourceAllocation)
                .where(
                    ResourceAllocation.worker_id == worker.id,
                    ResourceAllocation.released_at.is_(None),
                )
                .order_by(ResourceAllocation.lease_expires_at)
            )
        ).all()
    )
    return WorkerDetailResponse(
        worker=WorkerResponse.model_validate(worker),
        active_allocations=[
            ResourceAllocationResponse.model_validate(item) for item in allocations
        ],
    )


@router.post("/register", response_model=WorkerResponse)
async def register(
    body: WorkerRegister,
    _admin: AdministratorUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Worker:
    return await register_worker(
        session,
        body.name.strip(),
        body.total_cpu,
        body.total_memory_mb,
    )


@router.post("/{worker_id}/heartbeat", response_model=WorkerResponse)
async def heartbeat(
    worker_id: UUID,
    _admin: AdministratorUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Worker:
    worker = await heartbeat_worker(
        session,
        worker_id,
        get_settings().allocation_lease_seconds,
    )
    if worker is None:
        raise AppError("worker_not_found", "Worker was not found", 404)
    return worker
