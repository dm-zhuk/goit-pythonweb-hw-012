from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from pydantic import computed_field
from pydantic_settings import SettingsConfigDict
from src.services.base import settings


class TestSettings(settings):
    """Settings for tests."""

    JWT_SECRET: str = "1234567890"
    SMTP_PASSWORD: str = "1234567890"
    CLOUDINARY_CLOUD_NAME: str = "contacts_db_cloud"
    CLOUDINARY_API_KEY: int = 1234567890
    CLOUDINARY_API_SECRET: str = "1234567890"
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_contacts_db"
    )

    USE_TESTCONTAINERS: bool = True
    POSTGRES_TEMPLATE_DB: str = "template_test_contacts_db"
    POSTGRES_DB: str = "test_contacts_db"
    POSTGRES_PORT_EXTERNAL: int | None = None
    POSTGRES_DOCKER_IMAGE: str = "postgres:14-alpine"
    REDIS_DOCKER_IMAGE: str = "redis:7-alpine"
    REDIS_PORT_EXTERNAL: int | None = None
    ACCESS_TOKEN_EXP_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".testenv")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def get_template_postgres_uri(self) -> str:
        """Build database URI for DB template."""
        parsed = urlparse(self.DATABASE_URL)
        netloc = f"{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
        path = f"/{self.POSTGRES_TEMPLATE_DB}"
        return urlunparse((parsed.scheme, netloc, path, "", "", ""))


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=False)
def test_settings() -> TestSettings:
    """Settings for tests."""
    return TestSettings()


print("I'm in ", Path(__file__))
