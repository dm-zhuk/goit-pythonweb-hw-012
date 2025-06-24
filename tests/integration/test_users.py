import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.asyncio
@patch("src.services.email.send_verification_email", new_callable=AsyncMock)
async def test_register_user(client: AsyncClient):
    payload = {"email": "test@example.com", "password": "strongpassword"}

    response = await client.post("/api/users/register", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["email"] == "test@example.com"
    assert "id" in json_data
    assert not json_data["is_verified"]
