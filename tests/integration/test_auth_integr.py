import pytest
from unittest.mock import AsyncMock
from sqlalchemy import select
from src.database.models import User
from tests.conftest import TestingSessionLocal
from src.services.auth import auth_service

user_data = {
    "email": "007@gmail.com",
    "password": "12345678",
}


@pytest.mark.asyncio
async def test_signup(client, monkeypatch):
    mock_send_email = AsyncMock()
    monkeypatch.setattr("src.services.email.send_reset_email", mock_send_email)

    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_repeat_signup(client, monkeypatch):
    mock_send_email = AsyncMock()
    monkeypatch.setattr("src.services.email.send_reset_email", mock_send_email)

    # First signup
    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == 201, response.text

    # Repeat signup
    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_login(client):
    async with TestingSessionLocal() as session:
        # Create user and mark as verified
        current_user = User(
            email=user_data["email"],
            hashed_password=auth_service.get_password_hash(user_data["password"]),
            is_verified=True,
        )
        session.add(current_user)
        await session.commit()

    response = client.post(
        "/api/users/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_wrong_password_login(client):
    async with TestingSessionLocal() as session:
        current_user = User(
            email=user_data["email"],
            hashed_password=auth_service.get_password_hash(user_data["password"]),
            is_verified=True,
        )
        session.add(current_user)
        await session.commit()

    response = client.post(
        "/api/users/login",
        data={"username": user_data["email"], "password": "wrong_password"},
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Invalid credentials"
