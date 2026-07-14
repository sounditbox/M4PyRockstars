from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.dependencies import ProductDep, SessionDep
from app.models import Product
from app.schemas import ProductRead, ProductCreate, ProductUpdate
from app.security import AdminRoleDep

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

SearchParam = Annotated[str | None, Query(min_length=2, max_length=50)]
LimitParam = Annotated[int, Query(ge=1, le=100)]
CategoryParam = Annotated[str | None, Query(min_length=2, max_length=40)]
@router.post(
    "",
    response_model=ProductRead,
    status_code=HTTP_201_CREATED,
)
def create_product(
        product_data: ProductCreate,
        session: SessionDep,
        _admin: AdminRoleDep,
):
    product = Product(
        **product_data.model_dump(mode="json")
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.get("", response_model=list[ProductRead], status_code=200,
            summary="Products endpoint",
            description="Products endpoint description", tags=["Products"])
def list_products(
        session: SessionDep,
        search: SearchParam = None,
        limit: LimitParam = 10,
        category: CategoryParam = None,
        only_available: bool = True,
) -> list[ProductRead]:
    statement = select(Product).order_by(Product.id)
    if search:
        statement = statement.filter(Product.title.ilike(f"%{search}%"))
    statement = statement.filter(Product.is_available == only_available)
    if category:
        statement = statement.filter(Product.category == category)
    return session.scalars(statement.limit(limit)).all()


@router.get("/{product_id}", response_model=ProductRead, status_code=200,
            summary="Product endpoint",
            description="Product endpoint description", tags=["Products"])
async def get_product(
        product: ProductDep,
) -> ProductRead:
    return product


@router.put("/{product_id}", response_model=ProductRead,
            tags=["Products"], status_code=200,
            summary="Update product endpoint",
            description="Update product endpoint description"
            )
def replace_product(
        product: ProductDep,
        product_data: ProductCreate,
        session: SessionDep,
        _admin: AdminRoleDep,
):
    for field, value in product_data.model_dump(mode="json").items():
        setattr(product, field, value)

    session.commit()
    session.refresh(product)
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
)
def update_product(
        product: ProductDep,
        product_data: ProductUpdate,
        session: SessionDep,
        _admin: AdminRoleDep,
):
    current = ProductRead.model_validate(product).model_dump(
        exclude={"id"}
    )
    patch = product_data.model_dump(exclude_unset=True)
    validated = ProductCreate.model_validate(current | patch)

    for field, value in validated.model_dump(mode="json").items():
        setattr(product, field, value)

    session.commit()
    session.refresh(product)
    return product


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
