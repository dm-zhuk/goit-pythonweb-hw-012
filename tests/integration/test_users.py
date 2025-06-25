import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.users import create_user, get_user_by_email, confirm_email
from src.schemas.schemas import UserCreate
from src.database.models import User


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.get_password_hash")
async def test_create_user(mock_get_password_hash, mock_get_user_by_email):
    # Arrange
    mock_get_user_by_email.return_value = None  # Simulate no existing user
    mock_get_password_hash.return_value = "hashed_password"
    db = AsyncMock()
    user_create_data = UserCreate(
        email="testuser@example.com", password="StrongPass123"
    )

    # Act
    user = await create_user(user_create_data, db)

    # Assert
    assert user.email == "testuser@example.com"
    assert user.hashed_password == "hashed_password"
    mock_get_user_by_email.assert_awaited_once_with("testuser@example.com", db)


@pytest.mark.asyncio
@patch("src.repository.users.select")
@patch("src.database.db.get_db", return_value=AsyncMock())
async def test_get_user_by_email(mock_get_db):
    # Arrange
    db = mock_get_db()
    mock_user = AsyncMock(
        id=1, email="testuser@example.com", is_verified=False, avatar_url=None
    )
    db.execute = AsyncMock(
        return_value=AsyncMock(
            scalars=AsyncMock(first=AsyncMock(return_value=mock_user))
        )
    )

    # Act
    user = await get_user_by_email("testuser@example.com", db)

    # Assert
    assert user.id == 1
    assert user.email == "testuser@example.com"


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.database.db.get_db", return_value=AsyncMock())
async def test_confirm_email(mock_get_user_by_email, mock_get_db):
    # Arrange
    db = mock_get_db()
    mock_user = AsyncMock(email="testuser@example.com", is_verified=False)
    mock_get_user_by_email.return_value = mock_user
    db.add = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Act
    await confirm_email("testuser@example.com", db)

    # Assert
    assert mock_user.is_verified is True
    db.add.assert_called_once_with(mock_user)
    db.commit.assert_awaited_once()
