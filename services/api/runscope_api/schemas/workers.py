from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from runscope_api.models import WorkerStatus


class WorkerRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    total_cpu: float = Field(gt=0, le=128)
    total_memory_mb: int = Field(gt=0, le=1_048_576)


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: WorkerStatus
    total_cpu: float
    available_cpu: float
    total_memory_mb: int
    available_memory_mb: int
    current_run_count: int
    last_heartbeat_at: datetime
    created_at: datetime
    updated_at: datetime


class ResourceAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    worker_id: UUID
    cpu: float
    memory_mb: int
    lease_expires_at: datetime
    released_at: datetime | None


class WorkerDetailResponse(BaseModel):
    worker: WorkerResponse
    active_allocations: list[ResourceAllocationResponse]
