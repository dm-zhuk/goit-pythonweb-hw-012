import pytest
from unittest.mock import AsyncMock, patch

from src.repository.users import create_user
from src.schemas.schemas import UserCreate


@pytest.mark.asyncio
@patch("src.repository.users.get_user_by_email", new_callable=AsyncMock)
@patch("src.services.auth.auth_service.get_password_hash")
async def test_create_user(mock_get_password_hash, mock_get_user_by_email):
    mock_get_user_by_email.return_value = None
    mock_get_password_hash.return_value = "hashed_password"
    db = AsyncMock()
    user_create_data = UserCreate(
        email="testuser@example.com", password="StrongPass123"
    )

    user = await create_user(user_create_data, db)

    assert user.email == "testuser@example.com"
    assert user.hashed_password == "hashed_password"
    mock_get_user_by_email.assert_awaited_once_with("testuser@example.com", db)
