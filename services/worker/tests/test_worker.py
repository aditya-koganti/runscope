from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from runscope_api.storage import LocalArtifactStore
from runscope_contracts import EventEnvelope
from runscope_worker.main import process_event


@pytest.mark.asyncio
async def test_worker_ignores_unrelated_event(tmp_path: Path) -> None:
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="worker.heartbeat",
        occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        correlation_id="test",
        worker_id=uuid4(),
    )

    assert not await process_event(event, LocalArtifactStore(tmp_path))
