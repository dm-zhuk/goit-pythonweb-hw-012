import pytest

from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.asyncio
@patch("src.services.email.send_verification_email", new_callable=AsyncMock)
async def test_register_user(mock_send_email, client):
    payload = {"email": "testuser@example.com", "password": "StrongPass123"}

    response = await client.post("/api/users/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    mock_send_email.assert_awaited_once()
