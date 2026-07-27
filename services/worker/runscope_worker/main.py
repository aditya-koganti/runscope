import asyncio
import logging
from contextlib import suppress
from uuid import UUID

from runscope_api.broker import KafkaEventConsumer
from runscope_api.config import get_settings
from runscope_api.db import SessionFactory
from runscope_api.live_events import LiveEventBus, build_live_event_bus
from runscope_api.logging import configure_logging
from runscope_api.middleware import correlation_id_context
from runscope_api.models import ProcessedMessage
from runscope_api.run_execution import execute_existing_run
from runscope_api.storage import ArtifactStore, build_artifact_store
from runscope_api.worker_registry import heartbeat_worker, register_worker
from runscope_contracts import EventEnvelope
from sqlalchemy import select

logger = logging.getLogger(__name__)
CONSUMER_NAME_PREFIX = "trusted-template-worker-v2"


async def process_event(
    event: EventEnvelope,
    store: ArtifactStore,
    live_bus: LiveEventBus | None = None,
    worker_id: UUID | None = None,
) -> bool:
    if (
        event.event_type != "run.assigned"
        or event.run_id is None
        or event.worker_id is None
        or (worker_id is not None and event.worker_id != worker_id)
    ):
        return False
    correlation_token = correlation_id_context.set(event.correlation_id)
    try:
        return await process_assignment(event, store, live_bus, worker_id)
    finally:
        correlation_id_context.reset(correlation_token)


async def process_assignment(
    event: EventEnvelope,
    store: ArtifactStore,
    live_bus: LiveEventBus | None,
    worker_id: UUID | None,
) -> bool:
    if event.run_id is None or event.worker_id is None:
        return False
    run_id = event.run_id
    active_worker_id = worker_id or event.worker_id
    consumer_name = f"{CONSUMER_NAME_PREFIX}:{active_worker_id}"
    async with SessionFactory() as session:
        processed = await session.scalar(
            select(ProcessedMessage.id).where(
                ProcessedMessage.event_id == event.event_id,
                ProcessedMessage.consumer_name == consumer_name,
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

        lease_token_value = event.payload.get("lease_token")
        lease_token = UUID(str(lease_token_value)) if lease_token_value else None
        await execute_existing_run(
            session,
            store,
            run_id,
            publish,
            active_worker_id,
            lease_token,
        )
        session.add(
            ProcessedMessage(
                event_id=event.event_id,
                consumer_name=consumer_name,
            )
        )
        await session.commit()
        return True


async def heartbeat_loop(worker_id: UUID) -> None:
    settings = get_settings()
    while True:
        await asyncio.sleep(settings.worker_heartbeat_seconds)
        try:
            async with SessionFactory() as session:
                worker = await heartbeat_worker(
                    session,
                    worker_id,
                    settings.allocation_lease_seconds,
                )
                if worker is None:
                    raise RuntimeError("Registered worker record no longer exists")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker heartbeat failed", extra={"worker_id": str(worker_id)})


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    store = build_artifact_store(settings)
    live_bus = build_live_event_bus(settings)
    async with SessionFactory() as session:
        worker = await register_worker(
            session,
            settings.worker_name,
            settings.worker_total_cpu,
            settings.worker_total_memory_mb,
        )
    consumer = KafkaEventConsumer(
        settings.broker_bootstrap_servers,
        settings.broker_topic,
        f"runscope-worker-{worker.id}",
    )
    heartbeat = asyncio.create_task(heartbeat_loop(worker.id))
    delay = 1.0
    try:
        while True:
            try:
                async for event in consumer.events():
                    try:
                        await process_event(event, store, live_bus, worker.id)
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
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
