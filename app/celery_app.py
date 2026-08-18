from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import Settings

REPORT_QUEUE_NAME = "reports"
DLX_NAME = "dlx"
DLQ_NAME = "dlq"
DLQ_ROUTING_KEY = "failed"
MAINTENANCE_QUEUE_NAME = "maintenance"


DEAD_LETTER_EXCHANGE = Exchange(DLX_NAME, type="direct", durable=True)
DEAD_LETTER_QUEUE = Queue(
    DLQ_NAME,
    exchange=DEAD_LETTER_EXCHANGE,
    routing_key=DLQ_ROUTING_KEY,
    durable=True,
)

REPORT_EXCHANGE = Exchange(
    REPORT_QUEUE_NAME,
    type="direct",
    durable=True,
)
REPORT_QUEUE = Queue(
    REPORT_QUEUE_NAME,
    exchange=REPORT_EXCHANGE,
    routing_key=REPORT_QUEUE_NAME,
    queue_arguments={
        "x-dead-letter-exchange": DLX_NAME,
        "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
    },
)
MAINTENANCE_EXCHANGE = Exchange(
    MAINTENANCE_QUEUE_NAME,
    type="direct",
    durable=True,
)
MAINTENANCE_QUEUE = Queue(
    MAINTENANCE_QUEUE_NAME,
    exchange=MAINTENANCE_EXCHANGE,
    routing_key=MAINTENANCE_QUEUE_NAME,
)


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
        task_queues=(REPORT_QUEUE, MAINTENANCE_QUEUE),
        task_routes={
            "app.tasks.generate_product_report": {
                "queue": REPORT_QUEUE_NAME,
                "declare": (REPORT_QUEUE, DEAD_LETTER_QUEUE),
            },
            "app.tasks.build_catalog_summary": {
                "queue": MAINTENANCE_QUEUE_NAME,
            },
        },
        task_default_queue=MAINTENANCE_QUEUE_NAME,
        beat_schedule={
            "catalog-summary-every-morning": {
                "task": "app.tasks.build_catalog_summary",
                "schedule": crontab(hour=8, minute=0),
            },
        },
    )
    return application


celery_app = create_celery_app()
