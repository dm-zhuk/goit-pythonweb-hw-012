import pytest
from unittest.mock import patch
from src.services.cloudinary_config import UploadFileService
from src.services.base import Settings


@pytest.fixture
def settings():
    return Settings(
        CLOUDINARY_CLOUD_NAME="test_cloud",
        CLOUDINARY_API_KEY="test_key",
        CLOUDINARY_API_SECRET="test_secret",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",  # Dummy values for other fields
        JWT_SECRET="secret",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRE_MINUTES=30,
        SMTP_SERVER="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user",
        SMTP_PASSWORD="pass",
        MAIL_FROM_EMAIL="from@example.com",
        BASE_URL="http://localhost",
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="pass",
        POSTGRES_DB="db",
        PGADMIN_DEFAULT_EMAIL="admin@example.com",
        PGADMIN_DEFAULT_PASSWORD="admin",
    )


def test_upload_file_service_init(settings):
    # Setup mock
    with patch("src.services.upload_file.cloudinary.config") as mock_config:
        # Initialize service
        service = UploadFileService(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )

        # Assertions
        assert service.cloud_name == settings.CLOUDINARY_CLOUD_NAME
        assert service.api_key == settings.CLOUDINARY_API_KEY
        assert service.api_secret == settings.CLOUDINARY_API_SECRET
        mock_config.assert_called_once_with(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
