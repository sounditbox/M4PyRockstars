import pytest


def test_login_returns_bearer_token(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_read_current_user(client, admin_headers):
    response = client.get(
        "/api/v1/auth/me",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "disabled": False,
    }


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("missing-user", "any-password"),
        ("admin", "wrong-password"),
    ],
)
def test_login_rejects_invalid_credentials(
        client, username, password
):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Не удалось проверить учётные данные"
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_malformed_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Не удалось проверить учётные данные"
    }


def test_regular_user_cannot_create_product(client):
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "user", "password": "user"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Gaming Mouse",
            "category": "electronics",
            "price": 49.90,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Недостаточно прав"}
