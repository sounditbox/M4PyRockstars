from typing import Annotated

from fastapi import APIRouter, Query, Path
from starlette.concurrency import run_in_threadpool
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.cache import make_product_list_cache_key, get_json, set_json, \
    make_product_detail_cache_key, invalidate_product_cache
from app.dependencies import ProductDep, SessionDep, RedisDep, SettingsDep
from app.routers.product_service import query_products, read_product_from_db, \
    create_product_in_db, replace_product_in_db, update_product_in_db, \
    delete_product_from_db
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


@router.get("", response_model=list[ProductRead])
async def list_products(
        session: SessionDep,
        redis: RedisDep,
        settings: SettingsDep,
        search: SearchParam = None,
        limit: LimitParam = 10,
        category_slug: CategorySlugParam = None,
        only_available: bool = True,
) -> list[ProductRead]:
    cache_key = None
    if redis is not None:
        cache_key = await make_product_list_cache_key(
            redis,
            search=search,
            limit=limit,
            category_slug=category_slug,
            only_available=only_available,
        )
        cached = await get_json(redis, cache_key)
        if cached is not None:
            return [ProductRead.model_validate(item) for item in cached]

    response = await run_in_threadpool(
        query_products,
        session,
        search=search,
        limit=limit,
        category_slug=category_slug,
        only_available=only_available,
    )
    if redis is not None and cache_key is not None:
        await set_json(
            redis,
            cache_key,
            [item.model_dump(mode="json") for item in response],
            ttl_seconds=settings.product_cache_ttl_seconds,
        )
    return response


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
        product_id: Annotated[int, Path(ge=1)],
        session: SessionDep,
        redis: RedisDep,
        settings: SettingsDep,
) -> ProductRead:
    cache_key = make_product_detail_cache_key(product_id)
    if redis is not None:
        cached = await get_json(redis, cache_key)
        if cached is not None:
            return ProductRead.model_validate(cached)

    response = await run_in_threadpool(
        read_product_from_db,
        session,
        product_id,
    )
    if redis is not None:
        await set_json(
            redis,
            cache_key,
            response.model_dump(mode="json"),
            ttl_seconds=settings.product_cache_ttl_seconds,
        )
    return response


@router.post(
    "",
    response_model=ProductRead,
    status_code=HTTP_201_CREATED,
)
async def create_product(
        product_data: ProductCreate,
        session: SessionDep,
        redis: RedisDep,
        _admin: AdminRoleDep,
) -> ProductRead:
    response = await run_in_threadpool(
        create_product_in_db,
        session,
        product_data,
    )
    await invalidate_product_cache(redis)
    return response


@router.put("/{product_id}", response_model=ProductRead)
async def replace_product(
        product: ProductDep,
        product_data: ProductCreate,
        session: SessionDep,
        redis: RedisDep,
        _admin: AdminRoleDep,
) -> ProductRead:
    response = await run_in_threadpool(
        replace_product_in_db,
        session,
        product,
        product_data,
    )
    await invalidate_product_cache(redis, product_id=product.id)
    return response


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
        product: ProductDep,
        product_data: ProductUpdate,
        session: SessionDep,
        redis: RedisDep,
        _admin: AdminRoleDep,
) -> ProductRead:
    response = await run_in_threadpool(
        update_product_in_db,
        session,
        product,
        product_data,
    )
    await invalidate_product_cache(redis, product_id=product.id)
    return response


@router.delete(
    "/{product_id}",
    status_code=HTTP_204_NO_CONTENT,
)
async def delete_product(
        product: ProductDep,
        session: SessionDep,
        redis: RedisDep,
        _admin: AdminRoleDep,
) -> None:
    product_id = product.id
    await run_in_threadpool(
        delete_product_from_db,
        session,
        product,
    )
    await invalidate_product_cache(redis, product_id=product_id)
