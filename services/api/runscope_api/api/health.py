from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.db import SessionFactory

router = APIRouter(tags=["platform"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


async def database_status(session: AsyncSession) -> str:
    await session.execute(text("SELECT 1"))
    return "healthy"


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    try:
        async with SessionFactory() as session:
            status = await database_status(session)
        return ReadinessResponse(status="ready", dependencies={"postgresql": status})
    except Exception:
        return ReadinessResponse(
            status="not_ready",
            dependencies={"postgresql": "unavailable"},
        )
