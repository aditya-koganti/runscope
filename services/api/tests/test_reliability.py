import json
import logging
import sys
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from runscope_api.db import SessionFactory
from runscope_api.logging import JsonFormatter, redact
from runscope_api.models import OutboxMessage
from runscope_api.outbox import dispatch_batch
from runscope_api.storage import ArtifactStorageError, RetryingArtifactStore
from runscope_contracts import EventEnvelope
from sqlalchemy import select


class FlakyArtifactStore:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.attempts = 0

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        del key, data, content_type
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("controlled storage outage")

    async def get(self, key: str) -> bytes:
        del key
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("controlled storage outage")
        return b"artifact"


class FlakyBroker:
    def __init__(self) -> None:
        self.fail = True
        self.published = 0

    async def publish(self, topic: str, key: str, event: EventEnvelope) -> None:
        del topic, key, event
        if self.fail:
            raise ConnectionError("controlled broker outage")
        self.published += 1


@pytest.mark.asyncio
async def test_artifact_store_retries_are_bounded() -> None:
    transient = FlakyArtifactStore(failures=2)
    store = RetryingArtifactStore(transient, max_attempts=3, base_delay_seconds=0)
    await store.put("run/model", b"model", "application/octet-stream")
    assert transient.attempts == 3

    unavailable = FlakyArtifactStore(failures=10)
    store = RetryingArtifactStore(unavailable, max_attempts=3, base_delay_seconds=0)
    with pytest.raises(ArtifactStorageError):
        await store.get("run/model")
    assert unavailable.attempts == 3


@pytest.mark.asyncio
async def test_outbox_recovers_after_temporary_broker_failure() -> None:
    event = EventEnvelope(
        event_id=uuid4(),
        event_type="run.submitted",
        occurred_at=datetime.now(UTC),
        correlation_id="reliability-test",
        run_id=uuid4(),
    )
    async with SessionFactory() as session:
        message = OutboxMessage(
            topic="runscope.events.v1",
            partition_key=str(event.run_id),
            envelope=event.model_dump(mode="json"),
        )
        session.add(message)
        await session.commit()
        message_id = message.id

    broker = FlakyBroker()
    assert await dispatch_batch(broker, max_attempts=3) == 0
    async with SessionFactory() as session:
        failed = await session.get(OutboxMessage, message_id)
        assert failed is not None
        assert failed.publish_attempts == 1
        assert failed.last_error == "ConnectionError"

    broker.fail = False
    assert await dispatch_batch(broker, max_attempts=3) == 1
    assert broker.published == 1
    async with SessionFactory() as session:
        published = await session.scalar(
            select(OutboxMessage).where(OutboxMessage.id == message_id)
        )
        assert published is not None and published.published_at is not None


def test_structured_logging_redacts_sensitive_key_variants() -> None:
    payload = redact(
        {
            "password": "one",
            "access_token": "two",
            "s3_secret_key": "three",
            "safe": {"authorization_header": "four", "run_id": "visible"},
        }
    )
    assert payload == {
        "password": "[REDACTED]",
        "access_token": "[REDACTED]",
        "s3_secret_key": "[REDACTED]",
        "safe": {"authorization_header": "[REDACTED]", "run_id": "visible"},
    }

    record = logging.LogRecord("test", logging.INFO, "", 0, "safe message", (), None)
    record.run_id = "run-123"
    rendered = json.loads(JsonFormatter().format(record))
    assert rendered["message"] == "safe message"
    assert rendered["run_id"] == "run-123"

    try:
        raise RuntimeError("secret-looking exception detail")
    except RuntimeError:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            "",
            0,
            "stable failure message",
            (),
            exc_info=sys.exc_info(),
        )
    rendered = json.loads(JsonFormatter().format(record))
    assert rendered["message"] == "stable failure message"
    assert rendered["exception_type"] == "RuntimeError"
    assert "secret-looking" not in json.dumps(rendered)
