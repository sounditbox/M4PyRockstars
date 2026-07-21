from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import select

from app.database import create_database_engine, create_session_factory
from app.models import User
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    engine = create_database_engine(
        app.state.settings.database_url
    )

    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    settings = app.state.settings
    if settings.admin_username is not None:
        password = settings.admin_password
        if password is None:
            raise RuntimeError("Bootstrap admin password is not configured")
        with app.state.session_factory() as session:
            admin = session.scalar(
                select(User).where(
                    User.username == settings.admin_username
                )
            )
            if admin is None:
                session.add(User(
                    username=settings.admin_username,
                    role="admin",
                    hashed_password=hash_password(
                        password.get_secret_value()
                    ),
                ))
                session.commit()

    yield

    engine.dispose()
