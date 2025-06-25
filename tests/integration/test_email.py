import pytest
from unittest.mock import AsyncMock, patch
from fastapi_mail import FastMail, MessageSchema
from src.services.email import send_verification_email, send_reset_email


@pytest.mark.asyncio
@patch("src.services.email.FastMail")
async def test_send_verification_email(mock_fastmail):
    # Arrange
    mock_send_message = AsyncMock()
    mock_fastmail.return_value.send_message = mock_send_message

    email = "testuser@example.com"
    token = "mocked_token"
    base_url = "http://testserver"

    # Act
    await send_verification_email(email, token, base_url)

    # Assert
    mock_send_message.assert_awaited_once_with(
        MessageSchema(
            subject="Email Confirmation",
            recipients=[email],
            template_body={"host": base_url, "username": email, "token": token},
            subtype="html",
        ),
        template_name="email_template.html",
    )


@pytest.mark.asyncio
@patch("src.services.email.FastMail")
async def test_send_reset_email(mock_fastmail):
    # Arrange
    mock_send_message = AsyncMock()
    mock_fastmail.return_value.send_message = mock_send_message

    email = "testuser@example.com"
    token = "mocked_reset_token"
    base_url = "http://testserver"

    # Act
    await send_reset_email(email, token, base_url)

    # Assert
    mock_send_message.assert_awaited_once_with(
        MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            template_body={"host": base_url, "username": email, "token": token},
            subtype="html",
        ),
        template_name="email_template_reset.html",
    )
