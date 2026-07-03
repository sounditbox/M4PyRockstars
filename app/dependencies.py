from functools import lru_cache
from typing import Annotated, Iterator

import jwt
from fastapi import Depends, Path, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, \
    HTTP_401_UNAUTHORIZED

from app.core.config import Settings
from app.models import Product
from app.schemas import ProductRead, UserRead, TokenPayload
from app.storage import ProductStorage, UserStorage


def get_product_storage(request: Request) -> ProductStorage:
    return request.app.state.product_storage


def get_user_storage(request: Request) -> UserStorage:
    return request.app.state.user_storage



def get_product_or_404(
        product_id: Annotated[int, Path(ge=1)],
        session: SessionDep,
) -> Product:
    product = session.get(Product, product_id)
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

StorageDep = Annotated[
    ProductStorage,
    Depends(get_product_storage),
]

UserStorageDep = Annotated[
    UserStorage,
    Depends(get_user_storage),
]

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
        users: UserStorageDep,
        settings: SettingsDep,
) -> UserRead:
    try:
        token_data = decode_access_token(token, settings)
        user = users.get(int(token_data.sub))
    except (InvalidTokenError, ValidationError, ValueError):
        raise invalid_credentials()

    if user is None:
        raise invalid_credentials()

    return UserRead.model_validate(user.model_dump())


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
