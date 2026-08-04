from celery import Celery
from celery.schedules import crontab

from app.core.config import Settings


def create_celery_app(settings: Settings | None = None) -> Celery:
    settings = settings or Settings()
    application = Celery(
        "products",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.tasks"],
    )
    application.conf.update(
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        task_track_started=True,
        task_send_sent_event=True,
        worker_send_task_events=True,
        result_expires=3600,
        timezone="UTC",
        enable_utc=True,
        task_default_queue="reports",
        broker_connection_retry_on_startup=True,
        beat_schedule={
            "catalog-summary-every-morning": {
                "task": "app.tasks.build_catalog_summary",
                "schedule": crontab(hour=8, minute=0),
            },
        },
    )
    return application


celery_app = create_celery_app()
