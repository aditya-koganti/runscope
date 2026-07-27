from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from runscope_api.middleware import correlation_id_context
from runscope_api.storage import LocalArtifactStore
from runscope_contracts import EventEnvelope
from runscope_worker import main as worker_main


@pytest.mark.asyncio
async def test_worker_ignores_unrelated_event(tmp_path: Path) -> None:
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="worker.heartbeat",
        occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        correlation_id="test",
        worker_id=uuid4(),
    )

    assert not await worker_main.process_event(event, LocalArtifactStore(tmp_path))


@pytest.mark.asyncio
async def test_worker_does_not_leak_message_correlation_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def process_assignment(*_args) -> bool:
        assert correlation_id_context.get() == "assigned-run"
        return True

    monkeypatch.setattr(worker_main, "process_assignment", process_assignment)
    original = correlation_id_context.set("outer-request")
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="run.assigned",
        occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        correlation_id="assigned-run",
        run_id=uuid4(),
        worker_id=uuid4(),
    )
    try:
        assert await worker_main.process_event(event, LocalArtifactStore(tmp_path))
        assert correlation_id_context.get() == "outer-request"
    finally:
        correlation_id_context.reset(original)
