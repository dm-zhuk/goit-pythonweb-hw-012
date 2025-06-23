import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
from src.services.auth import auth_service
from src.database.models import Role
from tests.factories import UserFactory
from tests.conftest import TestSettings
from redis.asyncio import Redis
from fastapi import UploadFile
from io import BytesIO
import json


@pytest.mark.integration
async def test_get_current_user_integration(
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_cache: Redis,
    test_settings: TestSettings,
):
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    with (
        patch("src.database.db.rc", new=test_cache),
        patch.object(auth_service, "settings", test_settings),
    ):
        await test_cache.set(f"user:{user.email}", json.dumps(user.to_dict()))
        response = await test_client.get("/api/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
        assert response.json()["roles"] == Role.user.value


@pytest.mark.integration
async def test_upload_file_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    mock_file = BytesIO(b"test image")
    with (
        patch("cloudinary.uploader.upload") as mock_upload,
        patch("cloudinary.CloudinaryImage.build_url") as mock_build_url,
    ):
        mock_upload.return_value = {"version": "123"}
        mock_build_url.return_value = (
            "https://res.cloudinary.com/testcloud/image/RestApp/test@example.com"
        )
        response = await test_client.post(
            "/api/users/avatar",
            files={"file": ("test.jpg", mock_file, "image/jpeg")},
        )
        assert response.status_code == 200
        assert (
            response.json()["avatar_url"]
            == "https://res.cloudinary.com/testcloud/image/RestApp/test@example.com"
        )


@pytest.mark.integration
async def test_upload_invalid_file(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    response = await test_client.post(
        "/api/users/avatar", files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only image files allowed"


@pytest.mark.integration
async def test_register_user(test_client: AsyncClient, test_db: AsyncSession):
    with patch("src.services.email.send_verification_email", AsyncMock()):
        response = await test_client.post(
            "/api/users/register",
            json={"email": "new@example.com", "password": "Password123"},
        )
        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"


@pytest.mark.integration
async def test_login_success(test_client: AsyncClient, test_db: AsyncSession):
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


@pytest.mark.integration
async def test_login_failed(test_client: AsyncClient):
    response = await test_client.post(
        "/api/users/login", data={"username": "wrong@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
async def test_verify_email(test_client: AsyncClient, test_db: AsyncSession):
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


@pytest.mark.integration
async def test_verify_email_invalid(test_client: AsyncClient, test_db: AsyncSession):
    response = await test_client.get("/api/users/verify?token=invalid")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid token"
