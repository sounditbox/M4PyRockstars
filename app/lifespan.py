from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import create_database_engine, create_session_factory
from app.models import Base
from app.schemas import ProductRead, UserInDB
from app.security import hash_password
from app.storage import ProductStorage, UserStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    engine = create_database_engine(
        app.state.settings.database_url
    )
    Base.metadata.create_all(bind=engine)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    app.state.user_storage = UserStorage()
    app.state.user_storage.set_storage(
        [UserInDB(
            id=1,
            username="admin",
            role="admin",
            hashed_password=hash_password('admin'))
            ,
            UserInDB(
                id=2,
                username="user",
                role="user",
                hashed_password=hash_password('user'))
        ]
    )

    # Запуск приложения
    yield

    engine.dispose()
    app.state.user_storage.clear()
