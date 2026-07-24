from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///./products.db"
    app_name: str = "Products API"
    debug: bool = False
    api_prefix: str = "/api/v1"
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: str | None = None
    admin_password: SecretStr | None = None
    mongodb_url: str | None = None
    mongodb_database: str = "products"

    @model_validator(mode="after")
    def validate_admin(self) -> Self:
        username_is_set = self.admin_username is not None
        password_is_set = self.admin_password is not None
        if username_is_set != password_is_set:
            raise ValueError(
                "Bootstrap admin username and password must be set together"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
