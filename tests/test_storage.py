from app.schemas import ProductCreate
from app.storage import ProductStorage


def test_storage_assigns_sequential_ids():
    storage = ProductStorage()
    data = ProductCreate(
        name="Gaming Mouse",
        category="electronics",
        price=49.90,
    )

    first = storage.create(data)
    second = storage.create(data)

    assert first.id == 1
    assert second.id == 2
