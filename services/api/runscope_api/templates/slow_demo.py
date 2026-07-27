from pydantic import BaseModel, ConfigDict, Field


class SlowDemoParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_seconds: float = Field(
        default=8,
        ge=2,
        le=30,
        description="Approximate wall-clock duration of this demonstration workload.",
    )
    interval_seconds: float = Field(
        default=1,
        ge=0.25,
        le=2,
        description="How often the worker records honest completion progress.",
    )
    fail_intentionally: bool = Field(
        default=False,
        description="End in a controlled failure for retry demonstrations.",
    )
