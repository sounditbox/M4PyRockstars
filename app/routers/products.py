from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.dependencies import ProductDep, SessionDep, get_category_or_404, \
    get_product_or_404
from app.models import Product, Category
from app.schemas import ProductRead, ProductCreate, ProductUpdate
from app.security import AdminRoleDep

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

SearchParam = Annotated[str | None, Query(min_length=2, max_length=50)]
LimitParam = Annotated[int, Query(ge=1, le=100)]
CategorySlugParam = Annotated[
    str | None,
    Query(min_length=2, max_length=40),
]


@router.post(
    "",
    response_model=ProductRead,
    status_code=HTTP_201_CREATED,
)
def create_product(
        product_data: ProductCreate,
        session: SessionDep,
        _admin: AdminRoleDep,
) -> Product:
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

    return get_product_or_404(product.id, session)


@router.get("", response_model=list[ProductRead])
def list_products(
        session: SessionDep,
        search: SearchParam = None,
        limit: LimitParam = 10,
        category_slug: CategorySlugParam = None,
        only_available: bool = True,
) -> list[Product]:
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

    return list(session.scalars(statement.limit(limit)))


@router.get("/{product_id}", response_model=ProductRead, status_code=200,
            summary="Product endpoint",
            description="Product endpoint description", tags=["Products"])
async def get_product(
        product: ProductDep,
) -> ProductRead:
    return product


@router.put("/{product_id}", response_model=ProductRead)
def replace_product(
        product: ProductDep,
        product_data: ProductCreate,
        session: SessionDep,
        _admin: AdminRoleDep,
) -> Product:
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
    return get_product_or_404(product.id, session)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
        product: ProductDep,
        product_data: ProductUpdate,
        session: SessionDep,
        _admin: AdminRoleDep,
) -> Product:
    current = ProductCreate.model_validate(product).model_dump()
    patch = product_data.model_dump(exclude_unset=True)
    validated = ProductCreate.model_validate(current | patch)

    category = get_category_or_404(
        validated.category_id,
        session,
    )
    for field, value in validated.model_dump(
            mode="json",
            exclude={"category_id"},
    ).items():
        setattr(product, field, value)

    product.category = category
    session.commit()
    return get_product_or_404(product.id, session)


@router.delete(
    "/{product_id}",
    status_code=HTTP_204_NO_CONTENT,
)
def delete_product(
        product: ProductDep,
        session: SessionDep,
        _admin: AdminRoleDep,
):
    session.delete(product)
    session.commit()
    return None
