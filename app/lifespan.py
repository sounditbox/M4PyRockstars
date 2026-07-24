from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pymongo import AsyncMongoClient
from sqlalchemy import select

from app.database import create_database_engine, create_session_factory
from app.models import User
from app.mongodb import ensure_product_attribute_indexes
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    engine = create_database_engine(
        app.state.settings.database_url
    )

    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    mongo_client: AsyncMongoClient | None = None
    app.state.mongo_database = None

    settings = app.state.settings
    try:
        if settings.admin_username is not None:
            password = settings.admin_password
            if password is None:
                raise RuntimeError(
                    "Bootstrap admin password is not configured"
                )
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

        if settings.mongodb_url is not None:
            mongo_client = AsyncMongoClient(
                settings.mongodb_url,
                tz_aware=True,
            )
            await mongo_client.admin.command("ping")
            app.state.mongo_database = mongo_client[
                settings.mongodb_database
            ]
            await ensure_product_attribute_indexes(
                app.state.mongo_database
            )
        yield
    finally:
        if mongo_client is not None:
            await mongo_client.close()
        engine.dispose()
