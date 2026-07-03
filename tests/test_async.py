import pytest
from asgi_lifespan import LifespanManager
from httpx2 import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_list_products_async(app):
    async with (LifespanManager(app) as manager):
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test"
                               ) as client:
            response = await client.get("/api/v1/products/")
    assert response.status_code == 200
