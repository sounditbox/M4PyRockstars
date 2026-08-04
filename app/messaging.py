from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust

PRODUCT_EVENTS_EXCHANGE = "products.events"
PRODUCT_AUDIT_QUEUE = "products.audit"


class RabbitPublisher:
    def __init__(self, connection, channel, exchange) -> None:
        self._connection = connection
        self._channel = channel
        self._exchange = exchange

    @classmethod
    async def connect(cls, url: str) -> RabbitPublisher:
        connection = await connect_robust(url)
        channel = await connection.channel(publisher_confirms=True)
        exchange = await channel.declare_exchange(
            PRODUCT_EVENTS_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )
        audit_queue = await channel.declare_queue(
            PRODUCT_AUDIT_QUEUE,
            durable=True,
        )
        await audit_queue.bind(exchange, routing_key="product.*")
        return cls(connection, channel, exchange)

    async def publish(
            self,
            routing_key: str,
            payload: dict[str, Any],
    ) -> str:
        event_id = str(uuid4())
        event = {
            "id": event_id,
            "type": routing_key,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        message = Message(
            body=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event_id,
            timestamp=datetime.now(UTC),
        )
        await self._exchange.publish(message, routing_key=routing_key)
        return event_id

    async def close(self) -> None:
        await self._channel.close()
        await self._connection.close()
