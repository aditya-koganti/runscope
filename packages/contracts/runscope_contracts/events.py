from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    """Stable v1 event envelope; payload schemas are registered by event type."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_version: int = Field(default=1, ge=1)
    event_type: str = Field(min_length=3, max_length=100)
    occurred_at: datetime
    correlation_id: str = Field(min_length=1, max_length=128)
    run_id: UUID | None = None
    worker_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
