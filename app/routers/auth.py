from fastapi import APIRouter
from pwdlib.exceptions import UnknownHashError

from app.dependencies import LoginForm, SessionDep, SettingsDep, \
    invalid_credentials, ActiveUserDep, LoginRateLimitDep
from app.schemas import Token, UserRead
from app.security import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
def login(
        _rate_limit: LoginRateLimitDep,
        form_data: LoginForm,
        session: SessionDep,
        settings: SettingsDep,
) -> Token:
    try:
        user = authenticate_user(
            session, form_data.username, form_data.password
        )
    except UnknownHashError:
        raise invalid_credentials()
    if user is None:
        raise invalid_credentials()

    token = create_access_token(str(user.id), settings)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def read_current_user(
        current_user: ActiveUserDep,
) -> UserRead:
    return current_user


