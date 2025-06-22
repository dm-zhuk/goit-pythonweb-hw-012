import pytest
from httpx import AsyncClient
from src.schemas.schemas import UserCreate
from src.services.auth import auth_service
from src.database.models import Role
from tests.factories import UserFactory
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_register_user(test_client: AsyncClient, test_db):
    with patch("src.services.email.send_verification_email", AsyncMock()):
        response = await test_client.post(
            "/api/users/register",
            json={"email": "new@example.com", "password": "Password123"},
        )
        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, test_db):
    user = await UserFactory.create_(
        db=test_db,
        email="login@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    response = await test_client.post(
        "/api/users/login",
        data={"username": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_failed(test_client: AsyncClient):
    response = await test_client.post(
        "/api/users/login", data={"username": "wrong@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_request_email(test_client: AsyncClient, test_db):
    user = await UserFactory.create_(
        db=test_db,
        email="unverified@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=False,
        roles=Role.user.value,
    )
    with patch("src.services.email.send_verification_email", AsyncMock()):
        response = await test_client.post(
            "/api/users/request_email", json={"email": "unverified@example.com"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Verification email sent successfully"


@pytest.mark.asyncio
async def test_verify_email(test_client: AsyncClient, test_db):
    user = await UserFactory.create_(
        db=test_db,
        email="verify@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=False,
        roles=Role.user.value,
    )
    token = await auth_service.create_email_token({"sub": user.email})
    response = await test_client.get(f"/api/users/verify?token={token}")
    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully"


@pytest.mark.asyncio
async def test_me_non_existent_user(test_client: AsyncClient, test_db, test_cache):
    token = await auth_service.create_access_token({"sub": "nonexistent@example.com"})
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=test_client.transport,
        base_url="http://test",
        headers=headers,
    ) as client:
        response = await client.get("/api/users/me")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_update_avatar_invalid_file(test_client: AsyncClient, test_db):
    response = await test_client.post(
        "/api/users/avatar", files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only image files allowed"


@pytest.mark.asyncio
async def test_password_reset_request_invalid_email(test_client: AsyncClient, test_db):
    token = await auth_service.create_access_token({"sub": "test@example.com"})
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=test_client.transport,
        base_url="http://test",
        headers=headers,
    ) as client:
        response = await client.post(
            "/api/users/password-reset/request", json={"email": "wrong@example.com"}
        )
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Can only request password reset for your own email"
        )
