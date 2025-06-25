import pytest
from unittest.mock import AsyncMock, patch
from src.services.auth import auth_service
from src.database.models import Role
from src.services.base import settings


@pytest.mark.asyncio
@patch("src.services.auth.jwt.encode")
async def test_create_access_token(mock_encode):
    # Arrange
    data = {"sub": "testuser@example.com"}
    mock_encode.return_value = "mocked_token"

    # Act
    token = await auth_service.create_access_token(data)

    # Assert
    assert token == "mocked_token"
    mock_encode.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.services.auth.jwt.encode")
async def test_create_email_token(mock_encode):
    # Arrange
    data = {"sub": "testuser@example.com"}
    mock_encode.return_value = "mocked_email_token"

    # Act
    token = await auth_service.create_email_token(data)

    # Assert
    assert token == "mocked_email_token"
    mock_encode.assert_called_once()


@pytest.mark.asyncio
@patch("src.services.auth.get_user_from_cache", new_callable=AsyncMock)
@patch("src.services.auth.jwt.decode")
async def test_get_current_user(mock_decode, mock_get_user_from_cache):
    # Arrange
    token = "mocked_token"
    mock_decode.return_value = {"sub": "testuser@example.com"}
    mock_get_user_from_cache.return_value = {"email": "testuser@example.com"}

    # Act
    user = await auth_service.get_current_user(token)

    # Assert
    assert user["email"] == "testuser@example.com"
    mock_get_user_from_cache.assert_awaited_once_with(
        "testuser@example.com", AsyncMock()
    )


@pytest.mark.asyncio
@patch("src.services.auth.jwt.decode")
async def test_get_email_from_token(mock_decode):
    # Arrange
    token = "mocked_token"
    mock_decode.return_value = {"sub": "testuser@example.com", "scope": "email_token"}

    # Act
    email = await auth_service.get_email_from_token(token)

    # Assert
    assert email == "testuser@example.com"


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.create_email_token", new_callable=AsyncMock)
@patch("src.services.auth.send_reset_email", new_callable=AsyncMock)
async def test_request_password_reset(
    mock_send_reset_email, mock_create_email_token, mock_get_user_by_email
):
    # Arrange
    mock_get_user_by_email.return_value = AsyncMock()
    mock_create_email_token.return_value = "mocked_email_token"
    email = "testuser@example.com"
    db = AsyncMock()

    # Act
    await auth_service.request_password_reset(email, db)

    # Assert
    mock_get_user_by_email.assert_awaited_once_with(email, db)
    mock_create_email_token.assert_awaited_once_with({"sub": email})
    mock_send_reset_email.assert_awaited_once_with(
        email, "mocked_email_token", str(settings.BASE_URL)
    )


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.rc.get", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.get_email_from_token", new_callable=AsyncMock)
async def test_reset_password(
    mock_get_email_from_token, mock_get, mock_get_user_by_email
):
    # Arrange
    token = "mocked_token"
    new_password = "NewStrongPass123"
    email = "testuser@example.com"
    mock_get.return_value = email
    mock_get_email_from_token.return_value = email
    mock_get_user_by_email.return_value = AsyncMock()

    db = AsyncMock()

    # Act
    await auth_service.reset_password(token, new_password, db)

    # Assert
    mock_get_user_by_email.assert_awaited_once_with(email, db)
    mock_get_email_from_token.assert_awaited_once_with(token)
    assert (
        mock_get_user_by_email.return_value.hashed_password == "hashed_password"
    )  # Verify password is updated


@pytest.mark.asyncio
async def test_get_current_admin():
    # Arrange
    user = {"roles": Role.admin.value}

    # Act
    admin_user = await auth_service.get_current_admin(user)

    # Assert
    assert admin_user == user
