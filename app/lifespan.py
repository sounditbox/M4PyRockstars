from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.schemas import ProductRead, UserInDB
from app.security import hash_password
from app.storage import ProductStorage, UserStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Инициализация storage
    app.state.product_storage = ProductStorage()
    app.state.user_storage = UserStorage()
    # app.state.product_storage.set_storage({
    #     1: ProductRead(
    #         **{"id": 1, "name": "Keyboard", "price": 99.0,
    #            "is_available": True,
    #            'category': "Electronics"}),
    #     2: ProductRead(
    #         **{"id": 2, "name": "Laptop", "price": 1999.0,
    #            "is_available": True,
    #            'category': "Electronics"}),
    #     3: ProductRead(
    #         **{"id": 3, "name": "Mouse", "price": 399.0,
    #            "is_available": False,
    #            'category': "Electronics"}),
    # })
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

    # Очистка storage
    app.state.product_storage.clear()
    app.state.user_storage.clear()
