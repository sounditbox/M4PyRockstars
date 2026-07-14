from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import create_database_engine, create_session_factory
from app.schemas import UserInDB
from app.security import hash_password
from app.storage import UserStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    engine = create_database_engine(
        app.state.settings.database_url
    )

    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    app.state.user_storage = UserStorage()
    settings = app.state.settings
    if settings.admin_username is not None:
        password = settings.admin_password
        if password is None:
            raise RuntimeError("Bootstrap admin password is not configured")
        app.state.user_storage.add(UserInDB(
            id=1,
            username=settings.admin_username,
            role="admin",
            hashed_password=hash_password(password.get_secret_value()),
        ))

    yield

    engine.dispose()
    app.state.user_storage.clear()
