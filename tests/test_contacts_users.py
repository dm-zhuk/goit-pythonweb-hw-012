import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from src.schemas.schemas import (
    UserCreate,
    UserResponse,
    Token,
    RequestEmail,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from src.database.models import User, Role
from io import BytesIO

client = TestClient(app)


@pytest.fixture
def user_dict():
    return {
        "id": 1,
        "email": "test@example.com",
        "is_verified": False,
        "avatar_url": None,
        "roles": Role.user.value,
    }


@pytest.fixture
def user_create():
    return UserCreate(email="test@example.com", password="password123")


@pytest.fixture
def user_response():
    return UserResponse(
        id=1,
        email="test@example.com",
        is_verified=False,
        avatar_url=None,
        roles=Role.user,
    )


@pytest.mark.asyncio
async def test_register_user_success(user_create, user_response):
    mock_user = AsyncMock(spec=User, email=user_create.email, **user_response.dict())
    with patch("src.routers.users.create_user", return_value=mock_user):
        with patch(
            "src.routers.users.auth_service.create_email_token", return_value="token"
        ):
            with patch("src.routers.users.send_verification_email") as mock_email:
                response = client.post("/api/users/register", json=user_create.dict())
                assert response.status_code == 201
                assert response.json()["email"] == "test@example.com"
                mock_email.assert_called_once()


@pytest.mark.asyncio
async def test_login_success(user_dict):
    mock_user = AsyncMock(email="test@example.com", hashed_password="hashed_password")
    with patch("src.routers.users.get_user_by_email", return_value=mock_user):
        with patch("src.routers.users.auth_service.verify_password", return_value=True):
            with patch(
                "src.routers.users.auth_service.create_access_token",
                return_value="token",
            ):
                response = client.post(
                    "/api/users/login",
                    data={"username": "test@example.com", "password": "password123"},
                )
                assert response.status_code == 200
                assert response.json() == {
                    "access_token": "token",
                    "token_type": "bearer",
                }


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    with patch("src.routers.users.get_user_by_email", return_value=None):
        with patch("src.routers.users.logger.warning") as mock_logger:
            response = client.post(
                "/api/users/login",
                data={"username": "test@example.com", "password": "wrong"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid credentials"
            mock_logger.assert_called_once()


@pytest.mark.asyncio
async def test_request_email_success():
    mock_user = AsyncMock(email="test@example.com", is_verified=False)
    with patch("src.routers.users.get_user_by_email", return_value=mock_user):
        with patch(
            "src.routers.users.auth_service.create_email_token", return_value="token"
        ):
            with patch("src.routers.users.send_verification_email") as mock_email:
                response = client.post(
                    "/api/users/request_email", json={"email": "test@example.com"}
                )
                assert response.status_code == 200
                assert (
                    response.json()["message"] == "Verification email sent successfully"
                )
                mock_email.assert_called_once()


@pytest.mark.asyncio
async def test_request_email_already_verified():
    mock_user = AsyncMock(email="test@example.com", is_verified=True)
    with patch("src.routers.users.get_user_by_email", return_value=mock_user):
        response = client.post(
            "/api/users/request_email", json={"email": "test@example.com"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already verified"


@pytest.mark.asyncio
async def test_verify_email_success():
    with patch(
        "src.routers.users.auth_service.get_email_from_token",
        return_value="test@example.com",
    ):
        with patch(
            "src.routers.users.get_user_by_email",
            return_value=AsyncMock(is_verified=False),
        ):
            with patch("src.routers.users.confirm_email") as mock_confirm:
                response = client.get("/api/users/verify?token=token")
                assert response.status_code == 200
                assert response.json()["message"] == "Email verified successfully"
                mock_confirm.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_users_me_success(user_dict):
    with patch(
        "src.routers.users.auth_service.get_current_user", return_value=user_dict
    ):
        with patch(
            "src.routers.users.RoleAccess.__call__", return_value=None
        ):  # Bypass RoleAccess
            with patch(
                "fastapi_limiter.depends.RateLimiter.__call__", return_value=None
            ):  # Bypass RateLimiter
                response = client.get("/api/users/me")
                assert response.status_code == 200
                assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_update_avatar_success(user_dict, user_response):
    mock_file = BytesIO(b"fake_image")
    mock_file.name = "test.jpg"
    mock_user = AsyncMock(**user_response.dict())
    with patch(
        "src.routers.users.upload_service.upload_file", return_value="http://avatar.url"
    ):
        with patch("src.routers.users.get_user_by_email", return_value=mock_user):
            with patch("src.routers.users.rc.delete") as mock_cache_delete:
                with patch("src.routers.users.RoleAccess.__call__", return_value=None):
                    with patch(
                        "fastapi_limiter.depends.RateLimiter.__call__",
                        return_value=None,
                    ):
                        response = client.patch(
                            "/api/users/me/avatar",
                            files={"file": ("test.jpg", mock_file, "image/jpeg")},
                        )
                        assert response.status_code == 200
                        assert response.json()["avatar_url"] == "http://avatar.url"
                        mock_cache_delete.assert_awaited_once_with(
                            "fetch_user:test@example.com"
                        )


@pytest.mark.asyncio
async def test_update_avatar_error(user_dict):
    mock_file = BytesIO(b"fake_image")
    mock_file.name = "test.jpg"
    with patch(
        "src.routers.users.upload_service.upload_file",
        side_effect=Exception("Upload error"),
    ):
        with patch(
            "src.routers.users.auth_service.get_current_user", return_value=user_dict
        ):
            with patch("src.routers.users.logger.error") as mock_logger:
                with patch("src.routers.users.RoleAccess.__call__", return_value=None):
                    with patch(
                        "fastapi_limiter.depends.RateLimiter.__call__",
                        return_value=None,
                    ):
                        response = client.patch(
                            "/api/users/me/avatar",
                            files={"file": ("test.jpg", mock_file, "image/jpeg")},
                        )
                        assert response.status_code == 500
                        assert response.json()["detail"] == "Failed to upload avatar"
                        mock_logger.assert_called_once()


@pytest.mark.asyncio
async def test_request_password_reset_success(user_dict):
    with patch("src.routers.users.auth_service.request_password_reset") as mock_reset:
        with patch(
            "src.routers.users.auth_service.get_current_user", return_value=user_dict
        ):
            with patch("src.routers.users.RoleAccess.__call__", return_value=None):
                response = client.post(
                    "/api/users/password-reset/request",
                    json={"email": "test@example.com"},
                )
                assert response.status_code == 200
                assert response.json()["message"] == "Password reset email sent"
                mock_reset.assert_awaited_once_with("test@example.com", AsyncMock())


@pytest.mark.asyncio
async def test_request_password_reset_wrong_email(user_dict):
    with patch(
        "src.routers.users.auth_service.get_current_user", return_value=user_dict
    ):
        with patch("src.routers.users.RoleAccess.__call__", return_value=None):
            response = client.post(
                "/api/users/password-reset/request", json={"email": "wrong@example.com"}
            )
            assert response.status_code == 403
            assert (
                response.json()["detail"]
                == "Can only request password reset for your own email"
            )


@pytest.mark.asyncio
async def test_reset_password_success():
    with patch("src.routers.users.auth_service.reset_password") as mock_reset:
        response = client.post(
            "/api/users/password-reset/confirm",
            json={"token": "token", "new_password": "newpassword123"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully"
        mock_reset.assert_awaited_once_with("token", "newpassword123", AsyncMock())
