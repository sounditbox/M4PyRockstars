from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_settings, get_current_active_user
from app.main import create_app
from app.schemas import UserRead


@pytest.fixture
def app(tmp_path: str) -> FastAPI:
    database_path = tmp_path / "test.db"
    settings = Settings(
        app_name="Products API Test",
        database_url=f"sqlite+pysqlite:///{database_path.as_posix()}",
        debug=False,
        api_prefix="/api/v1",
        jwt_secret_key="test-secret-not-for-production-but-it-is-30-chars-long-at-least",
        jwt_algorithm="HS256",
        access_token_expire_minutes=5,
    )
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def override_admin_user() -> UserRead:
    return UserRead(
        id=100,
        username="test-admin",
        role="admin",
        disabled=False,
    )


@pytest.fixture
def admin_client(app: FastAPI) -> Iterator[TestClient]:
    app.dependency_overrides[get_current_active_user] = (
        override_admin_user
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
