from celery import Celery
from celery.schedules import crontab

from app.core.config import Settings

REPORT_QUEUE = "reports"
MAINTENANCE_QUEUE = "maintenance"

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
        broker_connection_retry_on_startup=True,
        task_create_missing_queues=True,
        task_routes={
            "app.tasks.generate_product_report": {
                "queue": REPORT_QUEUE,
            },
            "app.tasks.build_catalog_summary": {
                "queue": MAINTENANCE_QUEUE,
            },
        },
        task_default_queue=MAINTENANCE_QUEUE,
        beat_schedule={
            "catalog-summary-every-morning": {
                "task": "app.tasks.build_catalog_summary",
                "schedule": crontab(hour=8, minute=0),
            },
        },
    )
    return application


celery_app = create_celery_app()
