from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdate":
        if self.name is None and self.description is None:
            raise ValueError("At least one field must be provided")
        if self.name is not None:
            self.name = self.name.strip()
        return self


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().lower() for value in values if value.strip()]
        if any(len(value) > 40 for value in normalized):
            raise ValueError("Tags must be at most 40 characters")
        return list(dict.fromkeys(normalized))


class ExperimentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def normalize_and_require_change(self) -> "ExperimentUpdate":
        if self.name is None and self.description is None and self.tags is None:
            raise ValueError("At least one field must be provided")
        if self.name is not None:
            self.name = self.name.strip()
        if self.tags is not None:
            tags = [value.strip().lower() for value in self.tags if value.strip()]
            if any(len(value) > 40 for value in tags):
                raise ValueError("Tags must be at most 40 characters")
            self.tags = list(dict.fromkeys(tags))
        return self


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str
    tags: list[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
