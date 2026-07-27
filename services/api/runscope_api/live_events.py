import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from redis.asyncio import Redis
from runscope_contracts import LiveEvent

from runscope_api.config import Settings, get_settings


class LiveEventBus(Protocol):
    async def publish(
        self, run_id: UUID, event_type: str, payload: dict[str, Any]
    ) -> LiveEvent: ...

    def subscribe(self, run_id: UUID) -> AsyncIterator[LiveEvent]: ...


class RedisLiveEventBus:
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def channel(run_id: UUID) -> str:
        return f"runscope:run:{run_id}"

    async def publish(self, run_id: UUID, event_type: str, payload: dict[str, Any]) -> LiveEvent:
        event = LiveEvent(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            run_id=run_id,
            payload=payload,
        )
        await self.redis.publish(self.channel(run_id), event.model_dump_json())
        return event

    async def subscribe(self, run_id: UUID) -> AsyncIterator[LiveEvent]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel(run_id))
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15,
                )
                if message is None:
                    yield LiveEvent(
                        event_id=uuid4(),
                        event_type="stream.heartbeat",
                        occurred_at=datetime.now(UTC),
                        run_id=run_id,
                    )
                    continue
                yield LiveEvent.model_validate(json.loads(message["data"]))
        finally:
            await pubsub.unsubscribe(self.channel(run_id))
            await pubsub.aclose()

    async def close(self) -> None:
        await self.redis.aclose()


def build_live_event_bus(settings: Settings) -> RedisLiveEventBus:
    return RedisLiveEventBus(settings.redis_url)


async def get_live_event_bus() -> AsyncIterator[LiveEventBus]:
    bus = build_live_event_bus(get_settings())
    try:
        yield bus
    finally:
        await bus.close()
