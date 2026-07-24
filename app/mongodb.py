from pymongo.asynchronous.database import AsyncDatabase


async def ensure_product_attribute_indexes(
    database: AsyncDatabase,
) -> None:
    await database["product_attributes"].create_index(
        "product_id",
        unique=True,
        name="uq_product_attributes_product_id",
    )
