import pytest
from unittest.mock import patch, AsyncMock
from src.services.email import send_verification_email, send_reset_email
from tests.conftest import TestSettings
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_send_verification_email_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_verification_email(
            "test@example.com", "token123", test_settings.BASE_URL
        )
        mock_fm.send_message.assert_called_once()
        assert mock_fm.send_message.call_args[0][0].subject == "Email Confirmation"
        assert mock_fm.send_message.call_args[0][0].recipients == ["test@example.com"]
        assert (
            f"{test_settings.BASE_URL}/api/users/verify?token=token123"
            in mock_fm.send_message.call_args[0][0].body
        )


@pytest.mark.integration
async def test_send_reset_email_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_reset_email("test@example.com", "token123", test_settings.BASE_URL)
        mock_fm.send_message.assert_called_once()
        assert mock_fm.send_message.call_args[0][0].subject == "Password Reset Request"
        assert mock_fm.send_message.call_args[0][0].recipients == ["test@example.com"]
        assert (
            f"{test_settings.BASE_URL}/api/users/password-reset/confirm?token=token123"
            in mock_fm.send_message.call_args[0][0].body
        )
