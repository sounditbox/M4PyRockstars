from datetime import datetime, UTC
from typing import Mapping, Any

from fastapi import APIRouter, HTTPException
from pymongo import ReturnDocument

from app.dependencies import ProductDep, MongoDatabaseDep
from app.schemas import ProductAttributesRead, ProductAttributesPut, \
    ProductAttributesPatch
from app.security import AdminRoleDep

router = APIRouter(
    prefix="/products",
    tags=["Product attributes"],
)


def attributes_to_read(
    document: Mapping[str, Any],
) -> ProductAttributesRead:
    payload = dict(document)
    payload["id"] = str(payload.pop("_id"))
    return ProductAttributesRead.model_validate(payload)


@router.put(
    "/{product_id}/attributes",
    response_model=ProductAttributesRead,
)
async def put_product_attributes(
    product: ProductDep,
    payload: ProductAttributesPut,
    database: MongoDatabaseDep,
    _admin: AdminRoleDep,
) -> ProductAttributesRead:
    now = datetime.now(UTC)
    document = await database["product_attributes"].find_one_and_update(
        {"product_id": product.id},
        {
            "$set": {
                "attributes": payload.attributes,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return attributes_to_read(document)


@router.get(
    "/{product_id}/attributes",
    response_model=ProductAttributesRead,
)
async def get_product_attributes(
    product: ProductDep,
    database: MongoDatabaseDep,
) -> ProductAttributesRead:
    document = await database["product_attributes"].find_one(
        {"product_id": product.id}
    )
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Характеристики товара не найдены",
        )
    return attributes_to_read(document)


@router.patch(
    "/{product_id}/attributes",
    response_model=ProductAttributesRead,
)
async def patch_product_attributes(
    product: ProductDep,
    payload: ProductAttributesPatch,
    database: MongoDatabaseDep,
    _admin: AdminRoleDep,
) -> ProductAttributesRead:
    changes = {
        f"attributes.{key}": value
        for key, value in payload.attributes.items()
    }
    # changes = dict(map(lambda (key, value): (f"attributes.{key}", value), payload.attributes.items()))
    changes["updated_at"] = datetime.now(UTC)
    document = await database["product_attributes"].find_one_and_update(
        {"product_id": product.id},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        raise HTTPException(404, "Характеристики не найдены")
    return attributes_to_read(document)


@router.delete("/{product_id}/attributes", status_code=204)
async def delete_product_attributes(
    product: ProductDep,
    database: MongoDatabaseDep,
    _admin: AdminRoleDep,
) -> None:
    result = await database["product_attributes"].delete_one(
        {"product_id": product.id}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Характеристики не найдены")
