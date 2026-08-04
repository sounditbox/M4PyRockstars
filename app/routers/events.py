from aio_pika.exceptions import AMQPError, ChannelInvalidStateError
from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_202_ACCEPTED, HTTP_503_SERVICE_UNAVAILABLE

from app.dependencies import ProductDep, RabbitPublisherDep
from app.schemas import ProductEventAccepted, ProductRead
from app.security import AdminRoleDep

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "/products/{product_id}",
    response_model=ProductEventAccepted,
    status_code=HTTP_202_ACCEPTED,
)
async def publish_product_snapshot(
        product: ProductDep,
        publisher: RabbitPublisherDep,
        _admin: AdminRoleDep,
) -> ProductEventAccepted:
    if publisher is None:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="RabbitMQ is unavailable",
        )

    payload = ProductRead.model_validate(product).model_dump(mode="json")
    try:
        event_id = await publisher.publish("product.snapshot", payload)
    except (AMQPError, ChannelInvalidStateError) as exc:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="RabbitMQ is unavailable",
        ) from exc
    return ProductEventAccepted(
        event_id=event_id,
        routing_key="product.snapshot",
    )
