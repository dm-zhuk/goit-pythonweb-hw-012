import pytest
from jose import jwt
from fastapi import HTTPException
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from src.services.auth import auth_service
from src.services.base import settings
from src.database.models import Role


def test_verify_password_and_hash():
    password = "secret123"
    hashed = auth_service.get_password_hash(password)
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrong", hashed)


@pytest.mark.asyncio
async def test_create_access_token_contains_expected_claims():
    data = {"sub": "test@example.com"}
    token = await auth_service.create_access_token(data, expires_delta=5)
    decoded = jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    assert decoded["sub"] == "test@example.com"
    assert decoded["scope"] == "access_token"


@pytest.mark.asyncio
async def test_create_email_token_contains_expected_claims():
    data = {"sub": "email@example.com"}
    token = await auth_service.create_email_token(data)
    decoded = jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    assert decoded["scope"] == "email_token"
    assert decoded["sub"] == "email@example.com"


@pytest.mark.asyncio
async def test_get_email_from_token_valid_scope():
    token = await auth_service.create_email_token({"sub": "test@example.com"})
    email = await auth_service.get_email_from_token(token)
    assert email == "test@example.com"


@pytest.mark.asyncio
async def test_get_email_from_token_invalid_scope():
    bad_token = await auth_service.create_access_token({"sub": "test@example.com"})
    with pytest.raises(HTTPException) as exc:
        await auth_service.get_email_from_token(bad_token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_email_from_token_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await auth_service.get_email_from_token("invalid.token.string")
    assert exc.value.status_code == 422
