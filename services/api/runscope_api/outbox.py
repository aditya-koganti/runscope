import asyncio
import logging
from datetime import UTC, datetime

from runscope_contracts import EventEnvelope
from sqlalchemy import select

from runscope_api.broker import Broker, KafkaBroker
from runscope_api.config import Settings
from runscope_api.db import SessionFactory
from runscope_api.models import OutboxMessage

logger = logging.getLogger(__name__)


async def dispatch_batch(
    broker: Broker,
    limit: int = 50,
    max_attempts: int = 10,
) -> int:
    async with SessionFactory() as session:
        messages = list(
            (
                await session.scalars(
                    select(OutboxMessage)
                    .where(
                        OutboxMessage.published_at.is_(None),
                        OutboxMessage.publish_attempts < max_attempts,
                    )
                    .order_by(OutboxMessage.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        published = 0
        for message in messages:
            try:
                await broker.publish(
                    message.topic,
                    message.partition_key,
                    EventEnvelope.model_validate(message.envelope),
                )
                message.published_at = datetime.now(UTC)
                message.last_error = None
                published += 1
            except Exception as exc:
                message.publish_attempts += 1
                message.last_error = type(exc).__name__[:500]
                logger.warning(
                    "Outbox publish failed",
                    extra={
                        "outbox_id": str(message.id),
                        "attempt": message.publish_attempts,
                        "correlation_id": message.envelope.get("correlation_id"),
                    },
                )
                break
        await session.commit()
        return published


async def run_outbox_dispatcher(settings: Settings) -> None:
    broker = KafkaBroker(settings.broker_bootstrap_servers)
    delay = settings.outbox_poll_seconds
    try:
        while True:
            try:
                published = await dispatch_batch(
                    broker,
                    max_attempts=settings.outbox_max_attempts,
                )
                delay = settings.outbox_poll_seconds if published else min(delay * 1.5, 5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox dispatcher iteration failed")
                delay = min(delay * 2, 5)
            await asyncio.sleep(delay)
    finally:
        await broker.stop()
