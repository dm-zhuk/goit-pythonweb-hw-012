import pytest
from unittest.mock import patch, AsyncMock, ANY
from src.services.auth import Auth


@pytest.fixture
def auth_service():
    return Auth()


@pytest.mark.asyncio
async def test_request_password_reset_success(auth_service):
    email = "test@example.com"

    with patch("src.repository.users.get_user_by_email") as mock_get_user_by_email:
        mock_get_user_by_email.return_value = AsyncMock()

        with patch("src.services.auth.send_reset_email") as mock_send_reset_email:
            with patch("src.services.auth.rc") as mock_redis:
                mock_redis.setex = AsyncMock()

                await auth_service.request_password_reset(email, AsyncMock())

                mock_get_user_by_email.assert_called_once_with(email, ANY)
                mock_send_reset_email.assert_called_once()
                mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_request_password_reset_user_not_found(auth_service):
    email = "notfound@example.com"

    with patch("src.repository.users.get_user_by_email") as mock_get_user_by_email:
        mock_get_user_by_email.return_value = None

        with pytest.raises(Exception, match="User not found"):
            await auth_service.request_password_reset(email, AsyncMock())
