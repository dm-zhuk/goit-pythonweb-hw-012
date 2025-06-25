import pytest
import importlib
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, UploadFile, Request
from jose import jwt
from src.services.email import send_verification_email, send_reset_email
from src.services.auth import auth_service
from src.services.base import Settings
from src.services.cloudinary_config import UploadFileService
from src.services.get_upload import get_upload_file_service
from src.services.roles import RoleAccess
from tests.conftest import TestSettings
from src.database.models import Role


# Reload auth_service to apply settings patch
def reload_auth_service():
    importlib.reload(importlib.import_module("src.services.auth"))
    from src.services.auth import auth_service

    return auth_service


# Email Service Tests
@pytest.mark.unit
async def test_send_verification_email_success():
    """Test sending verification email successfully."""
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_verification_email("test@example.com", "token123", "http://test")
        mock_fm.send_message.assert_called_once()
        call_args = mock_fm.send_message.call_args[0][0]
        assert call_args.subject == "Email Confirmation"
        assert call_args.recipients == ["test@example.com"]


@pytest.mark.unit
async def test_send_verification_email_failure():
    """Test sending verification email failure."""
    with patch("src.services.email.FastMail", side_effect=Exception("SMTP error")):
        with pytest.raises(Exception, match="SMTP error"):
            await send_verification_email("test@example.com", "token123", "http://test")


@pytest.mark.unit
async def test_send_reset_email_success():
    """Test sending password reset email successfully."""
    with patch("src.services.email.FastMail") as mock_fastmail:
        mock_fm = AsyncMock()
        mock_fastmail.return_value = mock_fm
        await send_reset_email("test@example.com", "token123", "http://test")
        mock_fm.send_message.assert_called_once()
        call_args = mock_fm.send_message.call_args[0][0]
        assert call_args.subject == "Password Reset Request"
        assert call_args.recipients == ["test@example.com"]


@pytest.mark.unit
async def test_send_reset_email_failure():
    """Test sending password reset email failure."""
    with patch("src.services.email.FastMail", side_effect=Exception("SMTP error")):
        with pytest.raises(Exception, match="SMTP error"):
            await send_reset_email("test@example.com", "token123", "http://test")


# Settings Tests
@pytest.mark.unit
def test_settings_initialization_valid():
    """Test Settings initialization with valid env vars."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://testuser:testpass@localhost:5433/testdb",
        JWT_SECRET="test-secret",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRE_MINUTES=60,
        CLOUDINARY_CLOUD_NAME="testcloud",
        CLOUDINARY_API_KEY="123",
        CLOUDINARY_API_SECRET="secret",
    )
    assert settings.JWT_SECRET == "test-secret"
    assert settings.CLOUDINARY_CLOUD_NAME == "testcloud"


# Auth Service Tests
@pytest.mark.unit
def test_verify_password():
    """Test password verification."""
    hashed_password = auth_service.get_password_hash("password123")
    assert auth_service.verify_password("password123", hashed_password) is True
    assert auth_service.verify_password("wrongpassword", hashed_password) is False


@pytest.mark.unit
def test_get_password_hash():
    """Test password hashing."""
    hashed = auth_service.get_password_hash("password123")
    assert hashed != "password123"
    assert auth_service.verify_password("password123", hashed) is True


@pytest.mark.unit
async def test_get_current_user_no_email(test_app, mock_db_session):
    """Test getting current user with no email in token."""
    with patch("src.services.auth.settings", new=TestSettings()):
        token = jwt.encode(
            {"scope": "access_token"}, TestSettings().JWT_SECRET, algorithm="HS256"
        )
        with pytest.raises(HTTPException) as exc:
            await auth_service.get_current_user(token, mock_db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Could not validate credentials"


@pytest.mark.unit
async def test_get_email_from_token_success(test_app):
    """Test getting email from valid email token."""
    with patch("src.services.auth.settings", new=TestSettings()):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        email = await auth_service_reloaded.get_email_from_token(token)
        assert email == "test@example.com"


@pytest.mark.unit
async def test_get_email_from_token_invalid_scope(test_app):
    """Test getting email from token with invalid scope."""
    with patch("src.services.auth.settings", new=TestSettings()):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "access_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.get_email_from_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid scope"


@pytest.mark.unit
async def test_get_email_from_token_jwt_error(test_app):
    """Test getting email with invalid JWT."""
    with patch("src.services.auth.settings", new=TestSettings()):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            "wrong-secret",
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.get_email_from_token(token)
        assert exc.value.status_code == 422
        assert exc.value.detail == "Invalid token"


@pytest.mark.unit
async def test_request_password_reset_user_not_found(mock_db_session, test_app):
    """Test requesting password reset for non-existent user."""
    with (
        patch("src.database.db.rc") as mock_rc,
        patch("src.services.auth.settings", new=TestSettings()),
        patch("src.repository.users.get_user_by_email", AsyncMock(return_value=None)),
    ):
        auth_service_reloaded = reload_auth_service()
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.request_password_reset(
                "test@example.com", mock_db_session
            )
        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"
        mock_rc.setex.assert_not_called()


@pytest.mark.unit
async def test_reset_password_success(mock_db_session, mock_user, test_app):
    """Test resetting password successfully."""
    with (
        patch("src.database.db.rc") as mock_rc,
        patch("src.services.auth.settings", new=TestSettings()),
        patch(
            "src.repository.users.get_user_by_email", AsyncMock(return_value=mock_user)
        ),
    ):
        print(f"Mock rc in test_reset_password_success: {mock_rc}")
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        mock_rc.get.return_value = "test@example.com"
        mock_rc.delete.return_value = 1
        await auth_service_reloaded.reset_password(
            token, "new_password", mock_db_session
        )
        assert auth_service_reloaded.verify_password(
            "new_password", mock_user.hashed_password
        )
        mock_rc.delete.assert_called_with(f"reset_token:{token}")


@pytest.mark.unit
async def test_reset_password_token_mismatch(mock_db_session, mock_user, test_app):
    """Test resetting password with token-email mismatch."""
    with (
        patch("src.database.db.rc") as mock_rc,
        patch("src.services.auth.settings", new=TestSettings()),
        patch(
            "src.repository.users.get_user_by_email", AsyncMock(return_value=mock_user)
        ),
    ):
        print(f"Mock rc in test_reset_password_token_mismatch: {mock_rc}")
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        mock_rc.get.return_value = "other@example.com"
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.reset_password(
                token, "new_password", mock_db_session
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "Token mismatch"


@pytest.mark.unit
async def test_reset_password_user_not_found(mock_db_session, test_app):
    """Test resetting password for non-existent user."""
    with (
        patch("src.database.db.rc") as mock_rc,
        patch("src.services.auth.settings", new=TestSettings()),
        patch("src.repository.users.get_user_by_email", AsyncMock(return_value=None)),
    ):
        print(f"Mock rc in test_reset_password_user_not_found: {mock_rc}")
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        mock_rc.get.return_value = "test@example.com"
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.reset_password(
                token, "new_password", mock_db_session
            )
        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"


@pytest.mark.unit
async def test_reset_password_invalid_token(mock_db_session, test_app):
    """Test resetting password with invalid token."""
    with (
        patch("src.database.db.rc") as mock_rc,
        patch("src.services.auth.settings", new=TestSettings()),
    ):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com", "scope": "email_token"},
            TestSettings().JWT_SECRET,
            algorithm="HS256",
        )
        mock_rc.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.reset_password(
                token, "new_password", mock_db_session
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid or expired token"


@pytest.mark.unit
async def test_get_current_user_jwt_error(test_app, mock_db_session):
    """Test getting current user with invalid JWT."""
    with patch("src.services.auth.settings", new=TestSettings()):
        auth_service_reloaded = reload_auth_service()
        token = jwt.encode(
            {"sub": "test@example.com"}, "wrong-secret", algorithm="HS256"
        )
        with pytest.raises(HTTPException) as exc:
            await auth_service_reloaded.get_current_user(token, mock_db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Could not validate credentials"


@pytest.mark.unit
async def test_get_current_admin_success(mock_user):
    """Test getting current admin user."""
    mock_user.roles = Role.admin.value
    result = await auth_service.get_current_admin(mock_user.to_dict())
    assert result["email"] == "test@example.com"
    assert result["roles"] == Role.admin.value


# Cloudinary Tests
@pytest.mark.unit
def test_upload_file_service_init():
    """Test UploadFileService initialization."""
    test_settings = TestSettings()
    with patch("cloudinary.config") as mock_config:
        service = UploadFileService(
            cloud_name=test_settings.CLOUDINARY_CLOUD_NAME,
            api_key=test_settings.CLOUDINARY_API_KEY,
            api_secret=test_settings.CLOUDINARY_API_SECRET,
        )
        mock_config.assert_called_once_with(
            cloud_name=test_settings.CLOUDINARY_CLOUD_NAME,
            api_key=test_settings.CLOUDINARY_API_KEY,
            api_secret=test_settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        assert service.cloud_name == test_settings.CLOUDINARY_CLOUD_NAME


@pytest.mark.unit
def test_upload_file_success():
    """Test uploading file to Cloudinary successfully."""
    test_settings = TestSettings()
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
        service = UploadFileService(
            cloud_name=test_settings.CLOUDINARY_CLOUD_NAME,
            api_key=test_settings.CLOUDINARY_API_KEY,
            api_secret=test_settings.CLOUDINARY_API_SECRET,
        )
        url = service.upload_file(mock_file, "testuser")
        mock_upload.assert_called_once_with(
            mock_file.file, public_id="RestApp/testuser", overwrite=True
        )
        assert url == "https://res.cloudinary.com/testcloud/image/RestApp/testuser.jpg"


@pytest.mark.unit
def test_upload_file_failure():
    """Test UploadFileService upload failure."""
    test_settings = TestSettings()
    mock_file = MagicMock(spec=UploadFile)
    mock_file.file = MagicMock()
    with patch("cloudinary.uploader.upload", side_effect=Exception("Upload error")):
        service = UploadFileService(
            cloud_name=test_settings.CLOUDINARY_CLOUD_NAME,
            api_key=test_settings.CLOUDINARY_API_KEY,
            api_secret=test_settings.CLOUDINARY_API_SECRET,
        )
        with pytest.raises(Exception, match="Failed to upload file: Upload error"):
            service.upload_file(mock_file, "testuser")


@pytest.mark.unit
def test_get_upload_file_service(test_app):
    """Test getting UploadFileService instance."""
    service = get_upload_file_service()
    assert isinstance(service, UploadFileService)
    assert service.cloud_name == TestSettings().CLOUDINARY_CLOUD_NAME


# Role Tests
@pytest.mark.unit
async def test_role_access_allowed(mock_user):
    """Test RoleAccess with allowed role."""
    role_access = RoleAccess(allowed_roles=[Role.user])
    request = MagicMock(spec=Request)
    result = await role_access(request, mock_user.to_dict())
    assert result["email"] == "test@example.com"
    assert result["roles"] == Role.user.value


@pytest.mark.unit
async def test_role_access_denied(mock_user):
    """Test RoleAccess with denied role."""
    role_access = RoleAccess(allowed_roles=[Role.admin])
    request = MagicMock(spec=Request)
    with pytest.raises(HTTPException) as exc:
        await role_access(request, mock_user.to_dict())
    assert exc.value.status_code == 403
    assert exc.value.detail == f"Access denied: {Role.user} not in {[Role.admin]}"
