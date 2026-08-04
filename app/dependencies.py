from __future__ import annotations
from functools import lru_cache
from typing import Annotated, Iterator, Optional

import jwt
from fastapi import Depends, Path, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import ValidationError
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, \
    HTTP_401_UNAUTHORIZED, HTTP_429_TOO_MANY_REQUESTS

from app.core.config import Settings
from app.messaging import RabbitPublisher
from app.models import Product, Category, User
from app.schemas import UserRead, TokenPayload


def get_redis(request: Request) -> Redis | None:
    return request.app.state.redis


RedisDep = Annotated[Optional[Redis], Depends(get_redis)]


def get_rabbit_publisher(request: Request) -> RabbitPublisher | None:
    return request.app.state.rabbit_publisher


RabbitPublisherDep = Annotated[
    RabbitPublisher | None,
    Depends(get_rabbit_publisher),
]


async def limit_login_attempts(
        request: Request,
        redis: RedisDep,
        settings: SettingsDep,
) -> None:
    if redis is None:
        return

    client_host = request.client.host if request.client else "unknown"
    key = f"auth:login:{client_host}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, 60)

    if attempts > settings.auth_rate_limit_per_minute:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
        )


LoginRateLimitDep = Annotated[None, Depends(limit_login_attempts)]


def get_mongo_database(request: Request) -> AsyncDatabase:
    database = request.app.state.mongo_database
    if database is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB is unavailable",
        )
    return database


MongoDatabaseDep = Annotated[
    AsyncDatabase,
    Depends(get_mongo_database),
]


def get_product_or_404(
        product_id: Annotated[int, Path(ge=1)],
        session: SessionDep,
) -> Product:
    statement = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    product = session.scalar(statement)
    if product is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Товар не найден",
        )
    return product


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]

ProductDep = Annotated[Product, Depends(get_product_or_404)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/token",
)

LoginForm = Annotated[
    OAuth2PasswordRequestForm,
    Depends(),
]

TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(
        token: TokenDep,
        session: SessionDep,
        settings: SettingsDep,
) -> UserRead:
    try:
        token_data = decode_access_token(token, settings)
        user = session.get(User, int(token_data.sub))
    except (InvalidTokenError, ValidationError, ValueError):
        raise invalid_credentials()

    if user is None:
        raise invalid_credentials()

    return UserRead.model_validate(user)


CurrentUserDep = Annotated[
    UserRead,
    Depends(get_current_user),
]


def get_current_active_user(user: CurrentUserDep) -> UserRead:
    if user.disabled:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован",
        )
    return user


ActiveUserDep = Annotated[
    UserRead,
    Depends(get_current_active_user),
]


def invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str, settings: Settings) -> TokenPayload:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "iat"]},
    )
    token_data = TokenPayload.model_validate(payload)

    if token_data.type != "access":
        raise InvalidTokenError("Unexpected token type")

    return token_data


def get_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_category_or_404(
        category_id: Annotated[int, Path(ge=1)],
        session: SessionDep) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Товар не найден",
        )
    return category


CategoryDep = Annotated[Category, Depends(get_category_or_404)]
