import pytest
from unittest.mock import patch, AsyncMock
from src.services.email import send_verification_email, send_reset_email


@pytest.mark.asyncio
async def test_send_verification_email_success():
    email = "test@example.com"
    token = "testtoken"
    base_url = "http://localhost"

    with patch("src.services.email.FastMail") as MockFastMail:
        mock_fastmail_instance = MockFastMail.return_value
        mock_fastmail_instance.send_message = AsyncMock()

        await send_verification_email(email, token, base_url)

        mock_fastmail_instance.send_message.assert_called_once()
        assert (
            mock_fastmail_instance.send_message.call_args[1]["template_name"]
            == "email_template.html"
        )


@pytest.mark.asyncio
async def test_send_verification_email_failure():
    email = "test@example.com"
    token = "testtoken"
    base_url = "http://localhost"

    with patch("src.services.email.FastMail") as MockFastMail:
        mock_fastmail_instance = MockFastMail.return_value
        mock_fastmail_instance.send_message = AsyncMock(
            side_effect=Exception("SMTP error")
        )

        with pytest.raises(Exception, match="SMTP error"):
            await send_verification_email(email, token, base_url)


@pytest.mark.asyncio
async def test_send_reset_email_success():
    email = "reset@example.com"
    token = "resettoken"
    base_url = "http://localhost"

    with patch("src.services.email.FastMail") as MockFastMail:
        mock_fastmail_instance = MockFastMail.return_value
        mock_fastmail_instance.send_message = AsyncMock()

        await send_reset_email(email, token, base_url)

        mock_fastmail_instance.send_message.assert_called_once()
        assert (
            mock_fastmail_instance.send_message.call_args[1]["template_name"]
            == "email_template_reset.html"
        )


@pytest.mark.asyncio
async def test_send_reset_email_failure():
    email = "reset@example.com"
    token = "resettoken"
    base_url = "http://localhost"

    with patch("src.services.email.FastMail") as MockFastMail:
        mock_fastmail_instance = MockFastMail.return_value
        mock_fastmail_instance.send_message = AsyncMock(
            side_effect=Exception("SMTP error")
        )

        with pytest.raises(Exception, match="SMTP error"):
            await send_reset_email(email, token, base_url)
