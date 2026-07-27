from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from runscope_api.models import RunStatus


class TrainingTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    description: str
    version: str
    parameter_schema: dict[str, Any]
    enabled: bool
    created_at: datetime


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID
    template_key: str = Field(min_length=1, max_length=100)
    template_version: str = Field(default="1.0.0", min_length=1, max_length=40)
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_cpu: float = Field(default=1.0, ge=0.1, le=4.0)
    requested_memory_mb: int = Field(default=512, ge=128, le=8192)
    priority: int = Field(default=0, ge=-10, le=10)
    notes: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class RunRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_overrides: dict[str, Any] = Field(default_factory=dict)


class RunMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    template_id: UUID
    status: RunStatus
    priority: int
    requested_cpu: float
    requested_memory_mb: int
    assigned_worker_id: UUID | None
    attempt_number: int
    parent_run_id: UUID | None
    created_by: UUID
    created_at: datetime
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    failure_message: str | None
    notes: str
    tags: list[str]
    version: int


class RunParameterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    value: Any


class RunMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    value: float
    step: int
    recorded_at: datetime


class RunLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int
    level: str
    message: str
    recorded_at: datetime


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mime_type: str
    size_bytes: int
    checksum: str
    created_at: datetime


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    previous_status: RunStatus | None
    new_status: RunStatus | None
    event_metadata: dict[str, Any]
    created_at: datetime


class RunCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_ids: list[UUID] = Field(min_length=2, max_length=5)


class RunComparisonItem(BaseModel):
    run: RunResponse
    parameters: dict[str, Any]
    metrics: dict[str, float]


class RunCompareResponse(BaseModel):
    items: list[RunComparisonItem]
    best_by_metric: dict[str, UUID]
