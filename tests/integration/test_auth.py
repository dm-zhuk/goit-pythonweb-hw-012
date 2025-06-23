import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from src.services.auth import auth_service
from src.database.models import Role, User
from tests.factories import UserFactory
from tests.conftest import TestSettings
from redis.asyncio import Redis
from jose import jwt


@pytest.mark.integration
async def test_request_password_reset_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    with (
        patch("src.services.email.send_reset_email", AsyncMock()),
        patch("src.database.db.rc", new=test_cache),
    ):
        with patch.object(auth_service, "settings", test_settings):
            await auth_service.request_password_reset("test@example.com", test_db)
            token_keys = [k async for k in test_cache.keys("reset_token:*")]
            assert len(token_keys) == 1
            assert await test_cache.get(token_keys[0]) == "test@example.com"


@pytest.mark.integration
async def test_reset_password_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("old_password"),
        is_verified=True,
        roles=Role.user.value,
    )
    token = jwt.encode(
        {"sub": "test@example.com", "scope": "email_token"},
        test_settings.JWT_SECRET,
        algorithm="HS256",
    )
    await test_cache.setex(f"reset_token:{token}", 3600, "test@example.com")
    with (
        patch("src.database.db.rc", new=test_cache),
        patch.object(auth_service, "settings", test_settings),
    ):
        await auth_service.reset_password(token, "new_password", test_db)
        await test_db.refresh(user)
        assert auth_service.verify_password("new_password", user.hashed_password)
        assert await test_cache.get(f"reset_token:{token}") is None


@pytest.mark.integration
async def test_reset_password_invalid_token(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    token = jwt.encode(
        {"sub": "test@example.com", "scope": "email_token"},
        test_settings.JWT_SECRET,
        algorithm="HS256",
    )
    with (
        patch("src.database.db.rc", new=test_cache),
        patch.object(auth_service, "settings", test_settings),
    ):
        with pytest.raises(HTTPException) as exc:
            await auth_service.reset_password(token, "new_password", test_db)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid or expired token"
