from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

PRODUCT_LIST_VERSION_KEY = "products:list:version"


async def get_product_list_version(redis: Redis) -> int:
    version = await redis.get(PRODUCT_LIST_VERSION_KEY)
    if version is None:
        return 0
    return int(version)


async def make_product_list_cache_key(
        redis: Redis,
        *,
        search: str | None,
        limit: int,
        category_slug: str | None,
        only_available: bool,
) -> str:
    version = await get_product_list_version(redis)
    return (
        f"products:list:v{version}:"
        f"search={search or ''}:"
        f"limit={limit}:"
        f"category={category_slug or ''}:"
        f"available={only_available}"
    )


def make_product_detail_cache_key(product_id: int) -> str:
    return f"product:detail:{product_id}"


async def get_json(redis: Redis, key: str) -> Any | None:
    value = await redis.get(key)
    if value is None:
        return None
    return json.loads(value)


async def set_json(
    redis: Redis,
    key: str,
    value: Any,
    ttl_seconds: int,
) -> None:
    await redis.set(
        key,
        json.dumps(value, ensure_ascii=False),
        ex=ttl_seconds,
    )


async def invalidate_product_cache(
    redis: Redis | None,
    *,
    product_id: int | None = None,
) -> None:
    if redis is None:
        return
    await redis.incr(PRODUCT_LIST_VERSION_KEY)
    if product_id is not None:
        await redis.delete(make_product_detail_cache_key(product_id))
