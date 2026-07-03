import pytest


def test_list_products(client):
    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_product_returns_404(client):
    product_id = 999

    response = client.get(f"/api/v1/products/{product_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Товар не найден"}


def test_create_product(admin_client):
    response = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Mechanical Keyboard",
            "category": "electronics",
            "price": 129.90,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["name"] == "Mechanical Keyboard"
    assert body["category"] == "electronics"
    assert body["price"] == 129.90


def test_created_product_appears_in_list(admin_client):
    create_response = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Gaming Mouse",
            "category": "electronics",
            "price": 49.90,
        },
    )
    product = create_response.json()

    list_response = admin_client.get("/api/v1/products")

    assert list_response.status_code == 200
    assert list_response.json() == [product]


def test_product_lifecycle(admin_client):
    created = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Gaming Mouse",
            "category": "electronics",
            "price": 49.90,
        },
    )
    product_id = created.json()["id"]

    read = admin_client.get(f"/api/v1/products/{product_id}")
    assert read.status_code == 200

    updated = admin_client.patch(
        f"/api/v1/products/{product_id}",
        json={"is_available": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_available"] is False

    deleted = admin_client.delete(
        f"/api/v1/products/{product_id}"
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = admin_client.get(f"/api/v1/products/{product_id}")
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "", "category": "electronics", "price": 10}, "name"),
        ({"name": "Gaming Mouse", "price": 10}, "category"),
        ({"name": "Gaming Mouse", "category": "electronics", "price": 0},
         "price"),
        ({"name": "Gaming Mouse", "category": "electronics", "price": -1},
         "price"),
    ],
    ids=["empty-name", "missing-category", "zero-price", "negative-price"],
)
def test_invalid_product_payload(admin_client, payload, field):
    response = admin_client.post("/api/v1/products", json=payload)

    assert response.status_code == 422
    locations = [error["loc"][-1] for error in response.json()["detail"]]
    assert field in locations
