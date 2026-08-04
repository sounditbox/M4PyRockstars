from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.dependencies import limit_login_attempts


class FakeRedis:
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        self.expirations: list[tuple[str, int]] = []

    async def incr(self, key: str) -> int:
        return self.attempts

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations.append((key, seconds))


def make_request(host: str = "test-client") -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=host))


@pytest.mark.anyio
async def test_login_rate_limit_sets_one_minute_window():
    redis = FakeRedis(attempts=1)

    await limit_login_attempts(
        make_request(),
        redis,
        Settings(),
    )

    assert redis.expirations == [("auth:login:test-client", 60)]


@pytest.mark.anyio
async def test_login_rate_limit_rejects_request_over_limit():
    redis = FakeRedis(attempts=6)

    with pytest.raises(HTTPException) as exc_info:
        await limit_login_attempts(
            make_request(),
            redis,
            Settings(auth_rate_limit_per_minute=5),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Too many login attempts"
