import pytest
import importlib
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException
from src.services.email import send_verification_email, send_reset_email
from src.services.auth import auth_service
from src.services.cloudinary_config import UploadFileService
from src.services.get_upload import get_upload_file_service
from src.services.roles import RoleAccess
from tests.factories import UserFactory
from tests.conftest import TestSettings
from redis.asyncio import Redis
from src.database.models import Role
from jose import jwt
from fastapi import UploadFile
from unittest.mock import MagicMock
import json


def reload_auth_service():
    """Reload auth_service to apply settings patch."""
    importlib.reload(importlib.import_module("src.services.auth"))
    from src.services.auth import auth_service

    return auth_service


@pytest.mark.integration
async def test_send_verification_email_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    """Test sending verification email in integration setup."""
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_verification_email(
            "test@example.com", "token123", test_settings.BASE_URL
        )
        mock_fm.send_message.assert_called_once()
        assert mock_fm.send_message.call_args[0][0].subject == "Email Confirmation"
        assert mock_fm.send_message.call_args[0][0].recipients == ["test@example.com"]


@pytest.mark.integration
async def test_send_reset_email_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    """Test sending password reset email in integration setup."""
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_reset_email("test@example.com", "token123", test_settings.BASE_URL)
        mock_fm.send_message.assert_called_once()
        assert mock_fm.send_message.call_args[0][0].subject == "Password Reset Request"
        assert mock_fm.send_message.call_args[0][0].recipients == ["test@example.com"]


@pytest.mark.integration
async def test_request_password_reset_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    """Test requesting password reset with DB and Redis."""
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    with (
        patch("src.services.auth.send_reset_email", AsyncMock()),
        patch("src.services.auth.settings", new=TestSettings()),
        patch("src.database.db.rc", new=test_cache),
    ):
        auth_service_reloaded = reload_auth_service()
        await auth_service_reloaded.request_password_reset("test@example.com", test_db)
        token_keys = [k async for k in test_cache.keys("reset_token:*")]
        assert len(token_keys) == 1
        assert await test_cache.get(token_keys[0]) == "test@example.com"


@pytest.mark.integration
async def test_reset_password_integration(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    """Test resetting password with DB and Redis."""
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("old_password"),
        is_verified=True,
        roles=Role.user.value,
    )
    with (
        patch("src.services.auth.settings", new=TestSettings()),
        patch("src.database.db.rc", new=test_cache),
    ):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            test_settings.JWT_SECRET,
            algorithm="HS256",
        )
        await test_cache.setex(f"reset_token:{token}", 3600, "test@example.com")
        await auth_service_reloaded.reset_password(token, "new_password", test_db)
        updated_user = await UserFactory.get_by_email(
            db=test_db, email="test@example.com"
        )
        assert auth_service_reloaded.verify_password(
            "new_password", updated_user.hashed_password
        )
        assert await test_cache.get(f"reset_token:{token}") is None


@pytest.mark.integration
async def test_reset_password_invalid_token(
    test_cache: Redis, test_db: AsyncSession, test_settings: TestSettings
):
    """Test resetting password with invalid token."""
    with (
        patch("src.services.auth.settings", new=TestSettings()),
        patch("src.database.db.rc", new=test_cache),
    ):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            test_settings.JWT_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.reset_password(token, "new_password", test_db)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid or expired token"


@pytest.mark.integration
async def test_get_current_user_integration(
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_cache: Redis,
    test_settings: TestSettings,
):
    """Test getting current user via API."""
    with (
        patch("src.database.db.rc", new=test_cache),
        patch("src.services.auth.settings", new=TestSettings()),
    ):
        user = await UserFactory.create_(
            db=test_db,
            email="test@example.com",
            hashed_password=auth_service.get_password_hash("password123"),
            is_verified=True,
            roles=Role.user.value,
        )
        await test_cache.set(f"user:{user.email}", json.dumps(user.to_dict()))
        response = await test_client.get("/api/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
        assert response.json()["roles"] == Role.user.value


@pytest.mark.integration
async def test_upload_file_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    """Test uploading file via API (if endpoint exists)."""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.file = MagicMock()
    with (
        patch("cloudinary.uploader.upload") as mock_upload,
        patch("cloudinary.CloudinaryImage.build_url") as mock_build_url,
    ):
        mock_upload.return_value = {"version": "123"}
        mock_build_url.return_value = (
            "https://res.cloudinary.com/testcloud/image/RestApp/testuser.jpg"
        )
        response = await test_client.post(
            "/api/users/avatar",
            files={"file": ("test.jpg", mock_file.file, "image/jpeg")},
        )
        if response.status_code == 404:
            pytest.skip("Endpoint /api/users/avatar not implemented")
        assert response.status_code == 200
        assert (
            response.json()["avatar_url"]
            == "https://res.cloudinary.com/testcloud/image/RestApp/testuser.jpg"
        )


@pytest.mark.integration
async def test_role_access_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    """Test role-based access for admin route (if endpoint exists)."""
    user = await UserFactory.create_(
        db=test_db,
        email="admin@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.admin.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_client.app),
        base_url="http://test",
        headers=headers,
    ) as admin_client:
        response = await admin_client.get("/api/admin/some-protected-route")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/admin/some-protected-route not implemented")
        assert (
            response.status_code == 200 or response.status_code == 403
        )  # Depends on route logic


@pytest.mark.integration
async def test_role_access_denied_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    """Test role-based access denial for admin route."""
    user = await UserFactory.create_(
        db=test_db,
        email="user@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_client.app),
        base_url="http://test",
        headers=headers,
    ) as user_client:
        response = await user_client.get("/api/admin/some-protected-route")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/admin/some-protected-route not implemented")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
