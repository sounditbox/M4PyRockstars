import pytest


def create_electronics_category(admin_client) -> dict:
    response = admin_client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )
    assert response.status_code == 201
    return response.json()


def test_list_products(client):
    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_product_returns_404(client):
    product_id = 999

    response = client.get(f"/api/v1/products/{product_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Товар не найден"}


def test_create_product_with_category(admin_client):
    category_response = admin_client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )
    category_id = category_response.json()["id"]

    product_response = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Mechanical Keyboard",
            "category_id": category_id,
            "price": 120.00,
            "stock_count": 5,
        },
    )

    assert product_response.status_code == 201
    body = product_response.json()
    assert body["category"]["slug"] == "electronics"
    assert "category_id" not in body


def test_filter_products_by_category_slug(admin_client):
    electronics = admin_client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    ).json()
    books = admin_client.post(
        "/api/v1/categories",
        json={"name": "Books", "slug": "books"},
    ).json()

    admin_client.post(
        "/api/v1/products",
        json={
            "title": "Mechanical Keyboard",
            "category_id": electronics["id"],
            "price": 120.00,
        },
    )
    admin_client.post(
        "/api/v1/products",
        json={
            "title": "Clean Code",
            "category_id": books["id"],
            "price": 39.00,
        },
    )

    response = admin_client.get(
        "/api/v1/products?category_slug=electronics"
    )

    assert response.status_code == 200
    products = response.json()
    assert [product["title"] for product in products] == [
        "Mechanical Keyboard"
    ]


def test_created_product_appears_in_list(admin_client):
    electronics = create_electronics_category(admin_client)
    create_response = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Gaming Mouse",
            "category_id": electronics["id"],
            "price": 49.90,
            "stock_count": 42,
        },
    )
    product = create_response.json()

    list_response = admin_client.get("/api/v1/products")

    assert list_response.status_code == 200
    assert list_response.json() == [product]


def test_search_products_by_title(admin_client):
    electronics = create_electronics_category(admin_client)
    for title in ("Gaming Mouse", "Mechanical Keyboard"):
        response = admin_client.post(
            "/api/v1/products",
            json={
                "title": title,
                "category_id": electronics["id"],
                "price": 49.90,
                "stock_count": 42,
            },
        )
        assert response.status_code == 201

    response = admin_client.get(
        "/api/v1/products",
        params={"search": "keyboard"},
    )

    assert response.status_code == 200
    assert [product["title"] for product in response.json()] == [
        "Mechanical Keyboard"
    ]


def test_product_lifecycle(admin_client):
    electronics = create_electronics_category(admin_client)
    created = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Gaming Mouse",
            "category_id": electronics["id"],
            "price": 49.90,
            "stock_count": 42,
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


def test_replace_product(admin_client):
    electronics = create_electronics_category(admin_client)
    created = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Gaming Mouse",
            "category_id": electronics["id"],
            "price": 49.90,
            "stock_count": 42,
        },
    )
    product_id = created.json()["id"]

    replaced = admin_client.put(
        f"/api/v1/products/{product_id}",
        json={
            "title": "Mechanical Keyboard",
            "category_id": electronics["id"],
            "price": 129.90,
            "is_available": False,
            "stock_count": 42,
        },
    )

    assert replaced.status_code == 200
    body = replaced.json()
    assert body["id"] == product_id
    assert body["title"] == "Mechanical Keyboard"
    assert body["category"]["slug"] == "electronics"
    assert body["price"] == 129.90
    assert body["is_available"] is False


def test_patch_product_title_and_stock(admin_client):
    electronics = create_electronics_category(admin_client)
    created = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Gaming Mouse",
            "category_id": electronics["id"],
            "price": 49.90,
            "stock_count": 42,
        },
    )
    product_id = created.json()["id"]

    response = admin_client.patch(
        f"/api/v1/products/{product_id}",
        json={"title": "Wireless Mouse", "stock_count": 10},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Wireless Mouse"
    assert response.json()["stock_count"] == 10


def test_patch_rejects_obsolete_name_field(admin_client):
    electronics = create_electronics_category(admin_client)
    created = admin_client.post(
        "/api/v1/products",
        json={
            "title": "Gaming Mouse",
            "category_id": electronics["id"],
            "price": 49.90,
        },
    )
    product_id = created.json()["id"]

    response = admin_client.patch(
        f"/api/v1/products/{product_id}",
        json={"name": "Wireless Mouse"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"title": "", "category_id": 1, "price": 10}, "title"),
        ({"title": "Gaming Mouse", "price": 10}, "category_id"),
        ({"title": "Gaming Mouse", "category_id": 1, "price": 0},
         "price"),
        ({"title": "Gaming Mouse", "category_id": 1, "price": -1},
         "price"),
        ({
            "title": "Gaming Mouse",
            "category_id": 1,
            "price": 10,
            "stock_count": -1,
        }, "stock_count"),
    ],
    ids=[
        "empty-title",
        "missing-category",
        "zero-price",
        "negative-price",
        "negative-stock",
    ],
)
def test_invalid_product_payload(admin_client, payload, field):
    response = admin_client.post("/api/v1/products", json=payload)

    assert response.status_code == 422
    locations = [error["loc"][-1] for error in response.json()["detail"]]
    assert field in locations
