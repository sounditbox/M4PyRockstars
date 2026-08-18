from datetime import UTC, datetime
import time

from celery.exceptions import Reject, SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.core.config import Settings
from app.database import create_database_engine, create_session_factory
from app.models import Category, Product
from app.schemas import ProductRead

logger = get_task_logger(__name__)


class TemporaryReportError(Exception):
    """Сбой, после которого отчёт имеет смысл попробовать снова."""


class PermanentReportError(Exception):
    """Сбой, после которого отчёт нужно отправить в DLQ."""


@celery_app.task(
    bind=True,
    name="app.tasks.generate_product_report",
    autoretry_for=(TemporaryReportError,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=2,
    retry_backoff_max=60,
    retry_jitter=True,
    acks_late=True,
    soft_time_limit=25,
    time_limit=30,
    acks_on_failure_or_timeout=False,
    reject_on_worker_lost=True,
)
def generate_product_report(
        self,
        category_slug: str | None = None,
        only_available: bool = True,
        limit: int = 100,
        simulate_work_seconds: int = 0,
        simulate_failures: int = 0,
        simulate_permanent_error: bool = False,
) -> dict:
    task_id = self.request.id
    engine = None

    try:
        if simulate_work_seconds:
            time.sleep(simulate_work_seconds)

        if self.request.retries < simulate_failures:
            logger.warning(
                "Task %s: simulate temporary error, attempt %s of %s",
                task_id,
                self.request.retries + 1,
                simulate_failures,
            )
            raise TemporaryReportError("Temporary error")

        if simulate_permanent_error:
            exc = PermanentReportError("Invalid report")
            logger.error(
                "Permanent report error",
                extra={"task_id": task_id},
            )
            raise Reject(exc, requeue=False)

        settings = Settings()
        engine = create_database_engine(settings.database_url)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            statement = (
                select(Product)
                .join(Product.category)
                .options(selectinload(Product.category))
                .order_by(Category.name, Product.title)
                .where(Product.is_available == only_available)
            )
            if category_slug is not None:
                statement = statement.where(
                    Category.slug == category_slug
                )
            products = session.scalars(statement.limit(limit)).all()
            rows = [
                ProductRead.model_validate(product).model_dump(mode="json")
                for product in products
            ]
    except SoftTimeLimitExceeded:
        logger.warning(
            "Task %s: soft time limit exceeded",
            task_id,
        )
        raise
    finally:
        if engine is not None:
            engine.dispose()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {
            "category_slug": category_slug,
            "only_available": only_available,
            "limit": limit,
        },
        "count": len(rows),
        "products": rows,
    }


@celery_app.task(name="app.tasks.build_catalog_summary")
def build_catalog_summary() -> dict:
    settings = Settings()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            total = session.scalar(select(func.count(Product.id))) or 0
            available = session.scalar(
                select(func.count(Product.id)).where(Product.is_available)
            ) or 0
            out_of_stock = session.scalar(
                select(func.count(Product.id)).where(
                    Product.stock_count == 0
                )
            ) or 0
    finally:
        engine.dispose()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total": total,
        "available": available,
        "out_of_stock": out_of_stock,
    }
