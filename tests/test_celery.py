import pytest
from celery.exceptions import Reject, SoftTimeLimitExceeded
from redis.exceptions import ConnectionError

from app import tasks
from app.celery_app import celery_app
from app.routers import jobs


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


def test_report_queue_uses_common_dead_letter_queue():
    queues = celery_app.amqp.queues
    report_queue = queues["reports"]

    assert set(queues) == {"reports", "maintenance"}
    assert report_queue.exchange.name == "reports"
    assert report_queue.routing_key == "reports"
    assert report_queue.queue_arguments == {
        "x-dead-letter-exchange": "dlx",
        "x-dead-letter-routing-key": "failed",
    }

    report_route = celery_app.amqp.router.route(
        {},
        "app.tasks.generate_product_report",
    )
    assert {queue.name for queue in report_route["declare"]} == {
        "reports",
        "dlq",
    }
    assert report_route["queue"].name == "reports"

    maintenance_route = celery_app.amqp.router.route(
        {},
        "app.tasks.build_catalog_summary",
    )
    assert maintenance_route["queue"].name == "maintenance"
    assert "declare" not in maintenance_route


def test_report_task_reliability_options():
    assert tasks.generate_product_report.acks_late is True
    assert tasks.generate_product_report.acks_on_failure_or_timeout is False
    assert tasks.generate_product_report.reject_on_worker_lost is True
    assert tasks.generate_product_report.soft_time_limit == 25
    assert tasks.generate_product_report.time_limit == 30


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


def test_temporary_report_errors_retry_then_succeed(
        admin_client,
        app,
        monkeypatch,
):
    create_product(admin_client)
    monkeypatch.setattr(tasks, "Settings", lambda: app.state.settings)

    result = tasks.generate_product_report.apply(
        kwargs={"limit": 10, "simulate_failures": 2},
    )

    assert result.successful()
    assert result.result["count"] == 1


def test_permanent_report_error_is_rejected_without_retry():
    result = tasks.generate_product_report.apply(
        kwargs={"simulate_permanent_error": True},
    )

    assert result.state == "REJECTED"
    assert isinstance(result.result, Reject)
    assert result.result.requeue is False


def test_soft_time_limit_is_propagated(monkeypatch):
    def raise_soft_time_limit(_seconds):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(tasks.time, "sleep", raise_soft_time_limit)

    with pytest.raises(SoftTimeLimitExceeded):
        tasks.generate_product_report.run(simulate_work_seconds=1)
