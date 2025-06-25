import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.database.db import get_user_from_db, get_user_from_cache, init_db, get_db


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
async def test_get_user_from_db(mock_get_user_by_email):
    # Arrange
    mock_get_user_by_email.return_value = AsyncMock(
        email="testuser@example.com", to_dict=lambda: {"email": "testuser@example.com"}
    )
    db = AsyncMock()

    # Act
    user = await get_user_from_db("testuser@example.com", db)

    # Assert
    assert user["email"] == "testuser@example.com"


@pytest.mark.asyncio
@patch("src.database.db.rc", new_callable=AsyncMock)
@patch("src.database.db.get_user_from_db", new_callable=AsyncMock)
async def test_get_user_from_cache(mock_get_user_from_db, mock_rc):
    # Arrange
    mock_rc.get.return_value = None  # Simulate cache miss
    mock_get_user_from_db.return_value = {"email": "testuser@example.com"}
    db = AsyncMock()

    # Act
    user = await get_user_from_cache("testuser@example.com", db)

    # Assert
    assert user["email"] == "testuser@example.com"
    mock_rc.setex.assert_awaited_once()  # Check that we attempted to cache the user


@pytest.mark.asyncio
async def test_init_db():
    # Arrange
    with patch("src.database.db.engine.begin", new_callable=AsyncMock) as mock_begin:
        mock_begin.return_value.__aenter__.return_value.run_sync = AsyncMock()

        # Act
        await init_db()

        # Assert
        mock_begin.assert_awaited_once()  # Ensure init_db was called


@pytest.mark.asyncio
@patch("src.database.db.async_session", new_callable=AsyncMock)
async def test_get_db(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db

    # Act
    async with get_db() as db:
        assert db == mock_db  # Ensure we got the mock session

    # Assert
    mock_async_session.assert_awaited_once()  # Check if the session was created
