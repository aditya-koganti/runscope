import asyncio
import logging

from runscope_api.broker import KafkaEventConsumer
from runscope_api.config import get_settings
from runscope_api.db import SessionFactory
from runscope_api.live_events import LiveEventBus, build_live_event_bus
from runscope_api.logging import configure_logging
from runscope_api.models import ProcessedMessage
from runscope_api.run_execution import execute_existing_run
from runscope_api.storage import ArtifactStore, build_artifact_store
from runscope_contracts import EventEnvelope
from sqlalchemy import select

logger = logging.getLogger(__name__)
CONSUMER_NAME = "trusted-template-worker-v1"


async def process_event(
    event: EventEnvelope,
    store: ArtifactStore,
    live_bus: LiveEventBus | None = None,
) -> bool:
    if event.event_type != "run.submitted" or event.run_id is None:
        return False
    run_id = event.run_id
    async with SessionFactory() as session:
        processed = await session.scalar(
            select(ProcessedMessage.id).where(
                ProcessedMessage.event_id == event.event_id,
                ProcessedMessage.consumer_name == CONSUMER_NAME,
            )
        )
        if processed is not None:
            return False

        async def publish(event_type: str, payload: dict[str, object]) -> None:
            if live_bus:
                try:
                    await live_bus.publish(run_id, event_type, payload)
                except Exception:
                    logger.warning(
                        "Live event publish failed; durable execution continues",
                        extra={"run_id": str(run_id), "event_type": event_type},
                    )

        await execute_existing_run(session, store, run_id, publish)
        session.add(
            ProcessedMessage(
                event_id=event.event_id,
                consumer_name=CONSUMER_NAME,
            )
        )
        await session.commit()
        return True


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    store = build_artifact_store(settings)
    live_bus = build_live_event_bus(settings)
    consumer = KafkaEventConsumer(
        settings.broker_bootstrap_servers,
        settings.broker_topic,
        CONSUMER_NAME,
    )
    delay = 1.0
    while True:
        try:
            async for event in consumer.events():
                try:
                    await process_event(event, store, live_bus)
                except Exception:
                    logger.exception(
                        "Worker event processing failed",
                        extra={"event_id": str(event.event_id)},
                    )
            delay = 1.0
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker broker loop failed; reconnecting")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 10)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
