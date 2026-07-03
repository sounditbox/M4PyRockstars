from typing import Annotated

from fastapi import APIRouter, Query, Path, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, \
    HTTP_204_NO_CONTENT

from app.dependencies import StorageDep, ProductDep
from app.schemas import ProductRead, ProductCreate, ProductUpdate
from app.security import AdminRoleDep

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

SearchParam = Annotated[str | None, Query(min_length=2, max_length=50)]
LimitParam = Annotated[int, Query(ge=1, le=100)]
CategoryParam = Annotated[str | None, Query(min_length=2, max_length=40)]
ProductID = Annotated[int, Path(ge=1, description="ID товара")]


@router.post("/", response_model=ProductRead, status_code=HTTP_201_CREATED,
             summary="Create product endpoint",
             description="Create product endpoint description",
             tags=["Products"])
async def create_product(product_data: ProductCreate,
                         storage: StorageDep,
                         admin_user: AdminRoleDep
                         ):
    return storage.create(product_data)


@router.get("/", response_model=list[ProductRead], status_code=200,
            summary="Products endpoint",
            description="Products endpoint description", tags=["Products"])
async def list_products(
        storage: StorageDep,
        search: SearchParam = None,
        limit: LimitParam = 10,
        category: CategoryParam = None,
        only_available: bool | None = None,
) -> list[ProductRead]:
    filtered_products = storage.list()

    if search:
        filtered_products = [
            product for product in filtered_products if
            search.lower() in product.name.lower()
        ]

    if only_available is not None:
        filtered_products = [
            product for product in filtered_products if
            product.is_available == only_available
        ]

    if category:
        filtered_products = [
            product for product in filtered_products if
            product.category.lower() == category.lower()
        ]

    return filtered_products[:limit]


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
        product_id: ProductID,
        product_data: ProductCreate,
        storage: StorageDep
):
    if not storage.get(product_id):
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Товар не найден",
        )

    product = ProductRead(id=product_id, **product_data.model_dump())
    storage.create(product)

    return product


@router.patch('/{product_id}', response_model=ProductRead,
              status_code=200,
              summary="partial update product endpoint",
              description="Partial update product endpoint description",
              tags=["Products"])
async def update_product(
        product_data: ProductUpdate,
        storage: StorageDep,
        product: ProductDep,
) -> ProductRead:
    candidate_data = product.model_dump() | product_data.model_dump(
        exclude_unset=True,
        exclude_none=True)
    candidate_data.pop("id")
    validated = ProductCreate.model_validate(candidate_data)
    return storage.update(product.id, validated)


@router.delete('/{product_id}', status_code=HTTP_204_NO_CONTENT,
               summary="Delete product endpoint",
               description="Delete product endpoint description",
               tags=["Products"]
               )
def delete_product(
        product: ProductDep,
        storage: StorageDep,
):
    storage.delete(product.id)
    return None

