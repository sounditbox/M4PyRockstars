from collections.abc import Iterator
import os
from pathlib import Path

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-for-module-import-use-only",
)

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_settings, get_current_active_user
from app.main import create_app
from app.models import User
from app.schemas import UserRead
from app.security import hash_password

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_migrations(database_url: str) -> None:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )
    command.upgrade(alembic_config, "head")


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    database_path = tmp_path / "test.db"
    settings = Settings(
        app_name="Products API Test",
        api_prefix="/api/v1",
        database_url=f"sqlite+pysqlite:///{database_path.as_posix()}",
        jwt_secret_key="test-secret-not-for-production-use-only",
        admin_username=None,
        admin_password=None,
        mongodb_url=None,
        redis_url=None,
    )

    run_migrations(settings.database_url)

    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


def seed_test_users(app: FastAPI) -> None:
    with app.state.session_factory() as session:
        session.add_all([
            User(
                id=1,
                username="admin",
                role="admin",
                hashed_password=hash_password("admin"),
            ),
            User(
                id=2,
                username="user",
                role="user",
                hashed_password=hash_password("user"),
            ),
        ])
        session.commit()


@pytest.fixture
def seed_users():
    return seed_test_users


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        seed_test_users(app)
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
        app.dependency_overrides.pop(get_current_active_user, None)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
