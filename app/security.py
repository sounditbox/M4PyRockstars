from datetime import datetime, timezone, timedelta
from typing import Annotated

import jwt
from fastapi import HTTPException, Depends
from pwdlib import PasswordHash
from starlette.status import HTTP_403_FORBIDDEN

from app.core.config import Settings
from app.dependencies import ActiveUserDep
from app.schemas import UserInDB, Role, UserRead
from app.storage import UserStorage

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hash_: str) -> bool:
    return password_hash.verify(password, hash_)


def authenticate_user(
        storage: UserStorage,
        username: str,
        password: str,
) -> UserInDB | None:
    user = storage.get_by_username(username)

    if user is None:
        verify_password(password, DUMMY_HASH)
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_access_token(subject: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )




def require_role(role: Role):
    def dependency(user: ActiveUserDep) -> UserRead:
        if user.role != role:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return dependency


AdminRoleDep = Annotated[
    UserRead,
    Depends(require_role("admin")),
]

UserRoleDep = Annotated[
    UserRead,
    Depends(require_role("user")),
]