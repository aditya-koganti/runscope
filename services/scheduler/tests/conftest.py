import os
from collections.abc import AsyncIterator

import pytest_asyncio

os.environ.setdefault("RUNSCOPE_DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("RUNSCOPE_OUTBOX_DISPATCHER_ENABLED", "false")

from runscope_api.db import Base, engine


@pytest_asyncio.fixture(autouse=True)
async def reset_scheduler_database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
