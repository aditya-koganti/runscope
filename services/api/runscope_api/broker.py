import json
from collections.abc import AsyncIterator
from typing import Protocol

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from runscope_contracts import EventEnvelope


class Broker(Protocol):
    async def publish(self, topic: str, key: str, event: EventEnvelope) -> None: ...


class KafkaBroker:
    def __init__(self, bootstrap_servers: str) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: value,
            key_serializer=lambda value: value.encode(),
            acks="all",
        )
        self._started = False

    async def start(self) -> None:
        if not self._started:
            await self._producer.start()
            self._started = True

    async def stop(self) -> None:
        if self._started:
            await self._producer.stop()
            self._started = False

    async def publish(self, topic: str, key: str, event: EventEnvelope) -> None:
        await self.start()
        await self._producer.send_and_wait(
            topic,
            event.model_dump_json().encode(),
            key=key,
        )


class KafkaEventConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
    ) -> None:
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    async def events(self) -> AsyncIterator[EventEnvelope]:
        await self._consumer.start()
        try:
            async for message in self._consumer:
                yield EventEnvelope.model_validate(json.loads(message.value))
                await self._consumer.commit()
        finally:
            await self._consumer.stop()
