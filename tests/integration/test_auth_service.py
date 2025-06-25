import pytest
from unittest.mock import AsyncMock, patch
from src.services.auth import auth_service
from src.database.models import Role
from src.services.base import settings


@pytest.mark.asyncio
@patch("src.services.auth.jwt.encode")
async def test_create_email_token(mock_encode):
    data = {"sub": "testuser@example.com"}
    mock_encode.return_value = "mocked_email_token"

    token = await auth_service.create_email_token(data)

    assert token == "mocked_email_token"
    mock_encode.assert_called_once()


@pytest.mark.asyncio
@patch("src.services.auth.jwt.decode")
async def test_get_email_from_token(mock_decode):
    token = "mocked_token"
    mock_decode.return_value = {"sub": "testuser@example.com", "scope": "email_token"}

    email = await auth_service.get_email_from_token(token)

    assert email == "testuser@example.com"


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.create_email_token", new_callable=AsyncMock)
@patch("src.services.auth.send_reset_email", new_callable=AsyncMock)
@patch("src.services.auth.rc.setex", new_callable=AsyncMock)
async def test_request_password_reset(
    mock_setex, mock_send_reset_email, mock_create_email_token, mock_get_user_by_email
):
    mock_get_user_by_email.return_value = AsyncMock()
    mock_create_email_token.return_value = "mocked_email_token"
    email = "testuser@example.com"
    db = AsyncMock()

    await auth_service.request_password_reset(email, db)

    mock_get_user_by_email.assert_awaited_once_with(email, db)
    mock_create_email_token.assert_awaited_once_with({"sub": email})
    mock_send_reset_email.assert_awaited_once_with(
        email, "mocked_email_token", str(settings.BASE_URL)
    )
    mock_setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_admin():
    user = {"roles": Role.admin.value}

    admin_user = await auth_service.get_current_admin(user)

    assert admin_user == user


@pytest.mark.asyncio
@patch("src.services.auth.jwt.encode")
async def test_create_access_token(mock_encode):
    data = {"sub": "testuser@example.com"}
    mock_encode.return_value = "mocked_token"

    token = await auth_service.create_access_token(data)

    assert token == "mocked_token"
    mock_encode.assert_called_once()


@pytest.mark.asyncio
@patch("src.services.auth.get_user_from_cache", new_callable=AsyncMock)
@patch("src.services.auth.jwt.decode")
async def test_get_current_user(mock_decode, mock_get_user_from_cache):
    token = "mocked_token"
    mock_decode.return_value = {"sub": "testuser@example.com"}
    mock_get_user_from_cache.return_value = {"email": "testuser@example.com"}

    db = AsyncMock()
    user = await auth_service.get_current_user(token, db=db)

    assert user["email"] == "testuser@example.com"
    mock_get_user_from_cache.assert_awaited_once_with("testuser@example.com", db)


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.rc.delete", new_callable=AsyncMock)
@patch("src.services.auth.rc.get", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.get_email_from_token", new_callable=AsyncMock)
async def test_reset_password(
    mock_get_email_from_token, mock_rc_get, mock_rc_delete, mock_get_user_by_email
):
    token = "mocked_token"
    new_password = "NewStrongPass123"
    email = "testuser@example.com"
    mock_rc_get.return_value = email
    mock_get_email_from_token.return_value = email

    mock_user = AsyncMock()
    mock_get_user_by_email.return_value = mock_user
    db = AsyncMock()

    await auth_service.reset_password(token, new_password, db)

    mock_get_user_by_email.assert_awaited_once_with(email, db)
    mock_get_email_from_token.assert_awaited_once_with(token)
    mock_rc_get.assert_awaited_once_with(f"reset_token:{token}")
    mock_rc_delete.assert_awaited_once_with(f"reset_token:{token}")
    db.commit.assert_awaited_once()
