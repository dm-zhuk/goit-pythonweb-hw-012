import os
from pathlib import Path
import pytest
import logging
import asyncio
from urllib.parse import urlparse
from redis.asyncio import Redis
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.redis import RedisContainer
from src.services.base import Settings
from src.database.db import get_db
from src.database.models import Base, Role
from src.services.auth import auth_service
from tests.factories import UserFactory
from tests.conftest import TestSettings

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SQL templates
DROP_TABLE_SQL = """DROP TABLE IF EXISTS {name} CASCADE;"""
SET_IS_TEMPLATE_SQL = """ALTER DATABASE {name} WITH is_template = true;"""
DROP_DATABASE_SQL = """DROP DATABASE IF EXISTS {name};"""
COPY_DATABASE_SQL = """CREATE DATABASE {name} TEMPLATE {template};"""


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Provide test settings aligned with .env."""
    return TestSettings(
        DATABASE_URL="postgresql+asyncpg://devops:admin@localhost:5432/contacts_db",
        JWT_SECRET="test-secret",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRE_MINUTES=60,
        CLOUDINARY_CLOUD_NAME="testcloud",
        CLOUDINARY_API_KEY="testkey",
        CLOUDINARY_API_SECRET="testsecret",
        SMTP_SERVER="sandbox.smtp.mailtrap.io",
        SMTP_PORT=2525,
        SMTP_USER="testuser",
        SMTP_PASSWORD="testpass",
        MAIL_FROM_EMAIL="test@example.com",
        BASE_URL="http://test",
        POSTGRES_USER="devops",
        POSTGRES_PASSWORD="admin",
        POSTGRES_DB="contacts_db",
        POSTGRES_TEMPLATE_DB="contacts_db_template",
        PGADMIN_DEFAULT_EMAIL="admin@gmail.com",
        PGADMIN_DEFAULT_PASSWORD="admin",
        REDIS_URI="redis://localhost:6379",
    )


@pytest.fixture(scope="session", autouse=True)
async def _setup_database(test_settings: TestSettings):
    """Clean up the template database before test session."""
    logger.debug("_setup_database")
    parsed = urlparse(test_settings.DATABASE_URL)
    template_url = f"{parsed.scheme}://{parsed.netloc}/contacts_db_template"
    engine = create_async_engine(url=template_url, echo=False)
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            await conn.execute(text("CREATE DATABASE contacts_db_template"))
            logger.debug("Created template database contacts_db_template")
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.error(f"Failed to create template database: {e}")
                raise
        await conn.execute(
            text(SET_IS_TEMPLATE_SQL.format(name="contacts_db_template"))
        )
        async with engine.begin() as conn:
            await conn.execute(text(DROP_TABLE_SQL.format(name="alembic_version")))
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def apply_migrations(db_url: str) -> None:
    """Apply Alembic migrations to the database."""
    alembic_directory = Path(__file__).parent.parent.parent
    original_dir = Path.cwd()
    try:
        os.chdir(alembic_directory)
        alembic_cfg = Config(f"{alembic_directory}/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(config=alembic_cfg, revision="head")
    finally:
        os.chdir(original_dir)


@pytest.fixture(scope="session", autouse=True)
def _migrate_database(_setup_database, test_settings: TestSettings):
    """Apply migrations to the template database."""
    logger.debug("_migrate_database")
    parsed = urlparse(test_settings.DATABASE_URL)
    template_url = f"{parsed.scheme}://{parsed.netloc}/contacts_db_template"
    apply_migrations(db_url=template_url)


@pytest.fixture(scope="function", autouse=True)
async def _copy_database(_migrate_database, test_settings: TestSettings):
    """Copy database from template for each test."""
    logger.debug("_copy_database")
    parsed = urlparse(test_settings.DATABASE_URL)
    postgres_url = f"{parsed.scheme}://{parsed.netloc}/postgres"
    engine = create_async_engine(url=postgres_url, echo=False)
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(
            text(DROP_DATABASE_SQL.format(name=test_settings.POSTGRES_DB))
        )
        raw_sql = COPY_DATABASE_SQL.format(
            name=test_settings.POSTGRES_DB,
            template=test_settings.POSTGRES_TEMPLATE_DB,
        )
        await conn.execute(text(raw_sql))
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(test_settings: TestSettings):
    """Provide database session for tests."""
    logger.debug("test_db")
    engine = create_async_engine(test_settings.DATABASE_URL)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for attempt in range(10):
            try:
                logger.debug(f"Attempt {attempt + 1}: Checking PostgreSQL readiness")
                await session.execute(text("SELECT 1"))
                logger.debug("PostgreSQL is ready")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(1)
        else:
            logger.error("PostgreSQL failed to become ready after 10 seconds")
            raise RuntimeError("PostgreSQL not ready")
        yield session
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_cache(test_settings: TestSettings):
    """Provide Redis session for tests."""
    logger.debug("test_cache")
    redis_client = Redis.from_url(test_settings.REDIS_URI, decode_responses=True)
    await redis_client.flushdb()
    yield redis_client
    await redis_client.flushdb()
    await redis_client.close()


@pytest.fixture(scope="session")
def test_app(test_settings: TestSettings):
    """Create test FastAPI application."""
    logger.debug("test_app")
    from src.main import app

    def override_get_settings() -> TestSettings:
        return test_settings

    app.dependency_overrides[Settings] = override_get_settings
    return app


@pytest.fixture(scope="function")
async def test_client(
    test_db: AsyncSession, test_app: FastAPI, test_settings: TestSettings
):
    """Provide authenticated test client."""
    logger.debug("test_client")
    test_app.dependency_overrides[get_db] = lambda: test_db
    hashed_password = auth_service.get_password_hash("password123")
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=hashed_password,
        is_verified=True,
        roles=Role.user.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers=headers,
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def unauthenticated_client(test_db: AsyncSession, test_app: FastAPI):
    """Provide unauthenticated test client."""
    logger.debug("unauthenticated_client")
    test_app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client
