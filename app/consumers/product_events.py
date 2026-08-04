import asyncio
import json

from aio_pika import ExchangeType, connect_robust

from app.core.config import Settings
from app.messaging import PRODUCT_AUDIT_QUEUE, PRODUCT_EVENTS_EXCHANGE


async def consume_product_events() -> None:
    settings = Settings()
    if settings.rabbitmq_url is None:
        raise RuntimeError("RABBITMQ_URL is not configured")

    connection = await connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(
            PRODUCT_EVENTS_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )
        queue = await channel.declare_queue(
            PRODUCT_AUDIT_QUEUE,
            durable=True,
        )
        await queue.bind(exchange, routing_key="product.*")

        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process(requeue=True):
                    event = json.loads(message.body.decode("utf-8"))
                    print(
                        f"[{event['type']}] "
                        f"event_id={event['id']} "
                        f"product_id={event['payload']['id']}"
                    )


if __name__ == "__main__":
    try:
        asyncio.run(consume_product_events())
    except KeyboardInterrupt:
        pass
