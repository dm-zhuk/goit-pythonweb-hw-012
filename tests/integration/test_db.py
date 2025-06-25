import pytest
from unittest.mock import AsyncMock, patch

from src.database.db import get_user_from_db, get_user_from_cache


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
async def test_get_user_from_db(mock_get_user_by_email):
    mock_get_user_by_email.return_value = AsyncMock(
        email="testuser@example.com", to_dict=lambda: {"email": "testuser@example.com"}
    )
    db = AsyncMock()

    user = await get_user_from_db("testuser@example.com", db)

    assert user["email"] == "testuser@example.com"


@pytest.mark.asyncio
@patch("src.database.db.rc", new_callable=AsyncMock)
@patch("src.database.db.get_user_from_db", new_callable=AsyncMock)
async def test_get_user_from_cache(mock_get_user_from_db, mock_rc):
    mock_rc.get.return_value = None
    mock_get_user_from_db.return_value = {"email": "testuser@example.com"}
    db = AsyncMock()

    user = await get_user_from_cache("testuser@example.com", db)

    assert user["email"] == "testuser@example.com"
    mock_rc.setex.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.async_session", new_callable=AsyncMock)
async def test_get_db(mock_async_session):
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    mock_async_session.return_value.__aexit__.assert_not_awaited()
    mock_db.rollback.assert_not_awaited()
    mock_db.commit.assert_not_awaited()
