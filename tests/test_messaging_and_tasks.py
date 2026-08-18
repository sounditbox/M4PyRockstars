import json
from uuid import UUID

import pytest
from aio_pika import DeliveryMode
from aio_pika.exceptions import AMQPError
from redis.exceptions import ConnectionError

from app.celery_app import celery_app
from app.messaging import RabbitPublisher
from app.routers import jobs
from app import tasks


class FakeExchange:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, message, routing_key: str) -> None:
        self.published.append((message, routing_key))


class FakeClosable:
    async def close(self) -> None:
        pass


class FakePublisher:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, routing_key: str, payload: dict) -> str:
        self.events.append((routing_key, payload))
        return "event-123"


def test_celery_uses_rabbitmq_redis_and_daily_beat_schedule():
    assert celery_app.conf.broker_url.startswith("amqp://")
    assert celery_app.conf.result_backend.startswith("redis://")
    assert celery_app.conf.task_default_queue == "maintenance"
    assert celery_app.conf.task_send_sent_event is True
    assert celery_app.conf.worker_send_task_events is True
    schedule = celery_app.conf.beat_schedule[
        "catalog-summary-every-morning"
    ]
    assert schedule["task"] == "app.tasks.build_catalog_summary"


def create_product(admin_client) -> dict:
    category = admin_client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )
    assert category.status_code == 201

    product = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Mechanical Keyboard",
            "category_id": category.json()["id"],
            "price": 120,
            "stock_count": 5,
        },
    )
    assert product.status_code == 201
    return product.json()


@pytest.mark.anyio
async def test_rabbit_publisher_uses_persistent_json_message():
    exchange = FakeExchange()
    publisher = RabbitPublisher(
        FakeClosable(),
        FakeClosable(),
        exchange,
    )

    event_id = await publisher.publish(
        "product.snapshot",
        {"id": 42, "title": "Keyboard"},
    )

    UUID(event_id)
    message, routing_key = exchange.published[0]
    body = json.loads(message.body.decode("utf-8"))
    assert routing_key == "product.snapshot"
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    assert body["id"] == event_id
    assert body["payload"]["id"] == 42


def test_product_event_endpoint_publishes_snapshot(admin_client):
    product = create_product(admin_client)
    publisher = FakePublisher()
    admin_client.app.state.rabbit_publisher = publisher

    response = admin_client.post(
        f"/api/v1/events/products/{product['id']}"
    )

    assert response.status_code == 202
    assert response.json() == {
        "event_id": "event-123",
        "routing_key": "product.snapshot",
    }
    assert publisher.events[0][0] == "product.snapshot"
    assert publisher.events[0][1]["id"] == product["id"]


def test_product_event_endpoint_requires_rabbitmq(admin_client):
    product = create_product(admin_client)

    response = admin_client.post(
        f"/api/v1/events/products/{product['id']}"
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "RabbitMQ is unavailable"}


def test_product_event_endpoint_handles_rabbitmq_failure(admin_client):
    product = create_product(admin_client)

    class BrokenPublisher:
        @staticmethod
        async def publish(*args, **kwargs):
            raise AMQPError("connection lost")

    admin_client.app.state.rabbit_publisher = BrokenPublisher()

    response = admin_client.post(
        f"/api/v1/events/products/{product['id']}"
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "RabbitMQ is unavailable"}


def test_start_product_report_returns_task_id(admin_client, monkeypatch):
    class FakeTask:
        id = "11111111-1111-1111-1111-111111111111"

    captured = {}

    def fake_delay(**kwargs):
        captured.update(kwargs)
        return FakeTask()

    monkeypatch.setattr(jobs.generate_product_report, "delay", fake_delay)

    response = admin_client.post(
        "/api/v1/jobs/product-reports",
        json={
            "category_slug": "electronics",
            "only_available": True,
            "limit": 25,
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "task_id": FakeTask.id,
        "status": "PENDING",
    }
    assert captured == {
        "category_slug": "electronics",
        "only_available": True,
        "limit": 25,
        "simulate_work_seconds": 0,
        "simulate_failures": 0,
        "simulate_permanent_error": False,
    }


def test_get_task_status_returns_result(admin_client, monkeypatch):
    task_id = "22222222-2222-2222-2222-222222222222"

    class FakeResult:
        status = "SUCCESS"
        result = {"count": 2}

        @staticmethod
        def ready():
            return True

        @staticmethod
        def successful():
            return True

        @staticmethod
        def failed():
            return False

    monkeypatch.setattr(
        jobs,
        "AsyncResult",
        lambda *args, **kwargs: FakeResult(),
    )

    response = admin_client.get(f"/api/v1/jobs/{task_id}")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": task_id,
        "status": "SUCCESS",
        "ready": True,
        "successful": True,
        "result": {"count": 2},
        "error": None,
    }


def test_get_task_status_handles_backend_failure(admin_client, monkeypatch):
    task_id = "33333333-3333-3333-3333-333333333333"

    class BrokenResult:
        @property
        def status(self):
            raise ConnectionError("redis is unavailable")

    monkeypatch.setattr(
        jobs,
        "AsyncResult",
        lambda *args, **kwargs: BrokenResult(),
    )

    response = admin_client.get(f"/api/v1/jobs/{task_id}")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Task result backend is unavailable"
    }


def test_celery_tasks_read_project_database(admin_client, app, monkeypatch):
    create_product(admin_client)
    monkeypatch.setattr(tasks, "Settings", lambda: app.state.settings)

    report = tasks.generate_product_report.run(limit=10)
    summary = tasks.build_catalog_summary.run()

    assert report["count"] == 1
    assert report["products"][0]["title"] == "Mechanical Keyboard"
    assert summary == {
        "generated_at": summary["generated_at"],
        "total": 1,
        "available": 1,
        "out_of_stock": 0,
    }
