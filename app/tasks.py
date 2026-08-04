from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.core.config import Settings
from app.database import create_database_engine, create_session_factory
from app.models import Category, Product
from app.schemas import ProductRead


@celery_app.task(name="app.tasks.generate_product_report")
def generate_product_report(
        category_slug: str | None = None,
        only_available: bool = True,
        limit: int = 100,
) -> dict:
    settings = Settings()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    try:
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
    finally:
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
