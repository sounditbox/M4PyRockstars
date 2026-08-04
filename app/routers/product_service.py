from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_category_or_404, get_product_or_404
from app.models import Product, Category
from app.schemas import ProductCreate, ProductRead, ProductUpdate


def query_products(
        session: Session,
        *,
        search: str | None,
        limit: int,
        category_slug: str | None,
        only_available: bool,
) -> list[ProductRead]:
    statement = (
        select(Product)
        .join(Product.category)
        .options(selectinload(Product.category))
        .order_by(Category.name, Product.title)
    )
    if search:
        statement = statement.where(
            Product.title.ilike(f"%{search}%")
        )
    statement = statement.where(
        Product.is_available == only_available
    )
    if category_slug:
        statement = statement.where(
            Category.slug == category_slug
        )

    products = session.scalars(statement.limit(limit)).all()
    return [
        ProductRead.model_validate(product)
        for product in products
    ]


def read_product_from_db(
        session: Session,
        product_id: int,
) -> ProductRead:
    product = get_product_or_404(product_id, session)
    return ProductRead.model_validate(product)


def create_product_in_db(
    session: Session,
    product_data: ProductCreate,
) -> ProductRead:
    category = get_category_or_404(
        product_data.category_id,
        session,
    )
    product = Product(
        **product_data.model_dump(
            mode="json",
            exclude={"category_id"},
        ),
        category=category,
    )
    session.add(product)
    session.commit()
    return ProductRead.model_validate(
        get_product_or_404(product.id, session)
    )


def replace_product_in_db(
    session: Session,
    product: Product,
    product_data: ProductCreate,
) -> ProductRead:
    category = get_category_or_404(
        product_data.category_id,
        session,
    )
    for field, value in product_data.model_dump(
        mode="json",
        exclude={"category_id"},
    ).items():
        setattr(product, field, value)
    product.category = category
    session.commit()
    return ProductRead.model_validate(
        get_product_or_404(product.id, session)
    )


def update_product_in_db(
    session: Session,
    product: Product,
    product_data: ProductUpdate,
) -> ProductRead:
    current = ProductCreate.model_validate(product).model_dump()
    patch = product_data.model_dump(exclude_unset=True)
    validated = ProductCreate.model_validate(current | patch)
    return replace_product_in_db(session, product, validated)


def delete_product_from_db(
    session: Session,
    product: Product,
) -> None:
    session.delete(product)
    session.commit()
