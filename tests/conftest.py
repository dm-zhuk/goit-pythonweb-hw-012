import pytest
from unittest.mock import AsyncMock, patch
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.services.auth import auth_service
from src.database.models import Role


class TestSettings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
    JWT_SECRET: str = "test-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    SMTP_SERVER: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = "testuser"
    SMTP_PASSWORD: str = "testpass"
    MAIL_FROM_EMAIL: str = "test@meta.ua"
    BASE_URL: str = "http://test"
    POSTGRES_USER: str = "testuser"
    POSTGRES_PASSWORD: str = "testpass"
    POSTGRES_DB: str = "testdb"
    POSTGRES_TEMPLATE_DB: str = "template_testdb"
    REDIS_URI: str = "redis://localhost:6380"
    CLOUDINARY_CLOUD_NAME: str = "testcloud"
    CLOUDINARY_API_KEY: str = "123"
    CLOUDINARY_API_SECRET: str = "secret"
    PGADMIN_DEFAULT_EMAIL: str = "admin@test.com"
    PGADMIN_DEFAULT_PASSWORD: str = "admin"

    model_config = SettingsConfigDict(env_file=None, extra="ignore")


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    return TestSettings()


@pytest.fixture(scope="function")
def mock_db_session():
    """Mock AsyncSession for unit tests."""
    mock_session = AsyncMock()
    mock_session.get_user_by_email = AsyncMock()
    mock_session.commit = AsyncMock(return_value=None)
    return mock_session


@pytest.fixture(scope="function")
def mock_user():
    """Mock User object for unit tests."""
    user = type(
        "User",
        (),
        {
            "id": 1,
            "email": "test@example.com",
            "hashed_password": auth_service.get_password_hash("password123"),
            "is_verified": False,
            "avatar_url": None,
            "roles": Role.user.value,
            "to_dict": lambda self: {
                "id": self.id,
                "email": self.email,
                "is_verified": self.is_verified,
                "avatar_url": self.avatar_url,
                "roles": self.roles,
            },
        },
    )()
    return user


@pytest.fixture(scope="function")
def test_app(mock_db_session):
    """FastAPI app with mocked dependencies."""
    from src.main import app
    from src.database.db import get_db, init_db
    from fastapi.security import OAuth2PasswordBearer

    with patch("src.main.init_db", AsyncMock()):
        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[auth_service.oauth2_scheme] = (
            lambda: OAuth2PasswordBearer(tokenUrl="/api/users/login")
        )
        yield app
        app.dependency_overrides.clear()
