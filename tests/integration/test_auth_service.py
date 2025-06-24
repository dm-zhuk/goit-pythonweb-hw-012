import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from src.services.auth import Auth, auth_service
from src.services.base import settings


@pytest.mark.asyncio
async def test_password_hash_and_verify():
    password = "mysecretpassword"
    hashed = auth_service.get_password_hash(password)
    assert hashed != password
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpass", hashed)


@pytest.mark.asyncio
async def test_get_current_user_success_and_failure(monkeypatch, async_session):
    # Patch get_user_from_cache to return dummy user
    monkeypatch.setattr(
        "src.database.db.get_user_from_cache",
        AsyncMock(return_value={"email": "test@example.com"}),
    )

    # Create a token manually for testing
    data = {"sub": "test@example.com"}
    token = await auth_service.create_access_token(data)

    user = await auth_service.get_current_user(token=token, db=async_session)
    assert user["email"] == "test@example.com"

    # Test invalid token raises HTTPException
    with pytest.raises(HTTPException):
        await auth_service.get_current_user(token="invalidtoken", db=async_session)


@pytest.mark.asyncio
async def test_request_password_reset_and_reset_password(monkeypatch, async_session):
    email = "testreset@example.com"

    # Mock get_user_by_email to return a user object with email and hashed_password
    class DummyUser:
        def __init__(self, email):
            self.email = email
            self.hashed_password = auth_service.get_password_hash("oldpass")

    monkeypatch.setattr(
        "src.repository.users.get_user_by_email",
        AsyncMock(return_value=DummyUser(email)),
    )

    # Patch send_reset_email to a dummy async func (to avoid sending real emails)
    monkeypatch.setattr("src.services.email.send_reset_email", AsyncMock())

    # Patch redis client rc.setex and rc.delete
    monkeypatch.setattr("src.database.db.rc.setex", AsyncMock())
    monkeypatch.setattr("src.database.db.rc.delete", AsyncMock())
    monkeypatch.setattr("src.database.db.rc.get", AsyncMock(return_value=email))

    # Test request_password_reset runs without error
    await auth_service.request_password_reset(email, async_session)
    # The send_reset_email and rc.setex should be called - verified by mock call count if desired

    # Test reset_password happy path
    token = await auth_service.create_email_token({"sub": email})

    # Also patch get_email_from_token to call the real method
    monkeypatch.setattr(
        auth_service, "get_email_from_token", AsyncMock(return_value=email)
    )

    # Reset password should update hashed_password and call db.commit
    commit_called = False

    async def dummy_commit():
        nonlocal commit_called
        commit_called = True

    async def dummy_refresh(user):
        return

    async_session.commit = dummy_commit
    async_session.refresh = dummy_refresh

    await auth_service.reset_password(token, "newpassword123", async_session)
    assert commit_called


@pytest.mark.asyncio
async def test_get_current_admin_allows_admin_and_denies_others():
    # Admin user
    admin_user = {"roles": "admin"}
    result = await auth_service.get_current_admin(admin_user)
    assert result == admin_user

    # Non-admin user should raise
    non_admin_user = {"roles": "user"}
    with pytest.raises(HTTPException):
        await auth_service.get_current_admin(non_admin_user)
