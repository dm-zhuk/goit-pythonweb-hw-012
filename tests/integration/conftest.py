import os
import pytest

from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import urlparse, urlunparse
from redis import Redis
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from tests.conftest import TestSettings
from tests.factories import UserFactory
from testcontainers.core.generic import DockerContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]
from testcontainers.redis import RedisContainer  # type: ignore[import-untyped]

from src.services.base import settings
from src.database.db import async_session, get_db
from src.database.metadata import MinimalBase
from src.services.auth import auth_service

DROP_TABLE_SQL = """DROP TABLE IF EXISTS {name} CASCADE;"""
SET_IS_TEMPLATE_SQL = """ALTER DATABASE {name} WITH is_template = true;"""
DROP_DATABASE_SQL = """DROP DATABASE IF EXISTS {name};"""
COPY_DATABASE_SQL = """CREATE DATABASE {name} TEMPLATE {template};"""


@pytest.fixture(scope="session", autouse=True)
def _database_container_instance(test_settings: TestSettings) -> DockerContainer | None:
    """Create a PostgreSQL container for tests."""
    print("_database_container_instance")
    if not test_settings.USE_TESTCONTAINERS:
        return None
    # Split database URI into components
    parsed = urlparse(test_settings.DATABASE_URI)
    # Create a PostgresSQL instance in Docker container
    container = PostgresContainer(
        image=test_settings.POSTGRES_DOCKER_IMAGE,
        dbname=test_settings.POSTGRES_TEMPLATE_DB,
        username=parsed.username,
        password=parsed.password,
    )
    if test_settings.POSTGRES_PORT_EXTERNAL:
        container = container.with_bind_ports(
            5432, test_settings.POSTGRES_PORT_EXTERNAL
        )
    # Start the container with PostgreSQL
    container_instance = container.start()
    # Save a new connection URL
    hostname = container_instance.get_container_host_ip()
    port = int(container_instance.get_exposed_port(5432))
    netloc = f"{parsed.username}:{parsed.password}@{hostname}:{port}"
    path = f"/{test_settings.POSTGRES_DB}"

    test_settings.DATABASE_URI = urlunparse((parsed.scheme, netloc, path, "", "", ""))

    return container_instance


@pytest.fixture(scope="session", autouse=True)
def _redis_container_instance(test_settings: TestSettings) -> RedisContainer | None:
    if not test_settings.USE_TESTCONTAINERS:
        return None
    container = RedisContainer(image=test_settings.REDIS_DOCKER_IMAGE)
    if test_settings.REDIS_PORT_EXTERNAL:
        container = container.with_bind_ports(6379, test_settings.REDIS_PORT_EXTERNAL)
    container_instance = container.start()
    test_settings.REDIS_URI = "redis://{host}:{port}".format(
        host=container_instance.get_container_host_ip(),
        port=container_instance.get_exposed_port(6379),
    )
    return container_instance


@pytest.fixture(scope="session", autouse=False)
async def _setup_database(
    test_settings: TestSettings, _database_container_instance
) -> None:
    """Clean up the database before test session."""
    print("_setup_database")
    engine = create_async_engine(
        url=test_settings.get_template_postgres_uri, echo=False
    )
    async with engine.begin() as conn:
        # Mark database as template
        await conn.execute(
            text(SET_IS_TEMPLATE_SQL.format(name=test_settings.POSTGRES_TEMPLATE_DB))
        )
        # Drop Alembic migrations table if it exists
        await conn.execute(text(DROP_TABLE_SQL.format(name="alembic_version")))
        # Drop all tables from MinimalBase metadata
        await conn.run_sync(MinimalBase.metadata.drop_all)

    await engine.dispose()


def apply_migrations(db_uri) -> None:
    """Apply Alembic migrations for the empty database."""
    alembic_directory = Path(__file__).parent.parent.parent

    # Save current working directory
    original_dir = Path.cwd()

    try:
        # Change to the alembic directory temporarily
        os.chdir(alembic_directory)
        alembic_cfg = Config(f"{alembic_directory}/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_uri)
        # Apply the migrations
        command.upgrade(config=alembic_cfg, revision="head")
    finally:
        # Restore the original working directory
        os.chdir(original_dir)


@pytest.fixture(scope="session", autouse=False)
def _migrate_database(
    _setup_database,
    test_settings: TestSettings,
) -> None:
    """Apply migrations to the test database."""
    print("_migrate_database")
    apply_migrations(db_uri=test_settings.get_template_postgres_uri)


@pytest.fixture(scope="function", autouse=False)
async def _copy_database(
    _migrate_database,
    test_settings: TestSettings,
) -> None:
    """Copy database from template."""
    print("_copy_database")
    engine = create_async_engine(
        url=test_settings.get_template_postgres_uri, echo=False
    )

    async with engine.connect() as conn:
        # Enable autocommit mode for DROP DATABASE
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        # Drop database if exists
        await conn.execute(
            text(DROP_DATABASE_SQL.format(name=test_settings.POSTGRES_DB))
        )
        # Create new database from template
        raw_sql = COPY_DATABASE_SQL.format(
            name=test_settings.POSTGRES_DB,
            template=test_settings.POSTGRES_TEMPLATE_DB,
        )
        await conn.execute(text(raw_sql))
    await engine.dispose()


@pytest.fixture(scope="function", autouse=False)
async def test_db(test_settings: TestSettings):
    """Override database session for tests."""
    print("test_db")
    test_sessionmanager = async_session(test_settings.DATABASE_URI)
    async with test_sessionmanager.session() as session:
        yield session


@pytest.fixture(scope="function", autouse=False)
async def test_cache(test_settings: TestSettings):
    """Override database session for tests."""
    print("test_cache")
    redis_client = Redis.from_url(url=test_settings.REDIS_URI, decode_responses=True)
    yield redis_client
    # Close the Redis connection when done
    redis_client.close()


@pytest.fixture(scope="function", autouse=False)
def test_app(_copy_database, test_db, test_settings: TestSettings) -> FastAPI:
    """Create test FastAPI application."""
    print("test_app")
    from src.main import app

    def override_get_settings() -> TestSettings:
        """Override settings for tests."""
        return test_settings

    def override_get_db() -> TestSettings:
        """Override database for tests."""
        return test_db

    async def override_get_uploader() -> AsyncMock:
        """Override uploader for tests."""
        return AsyncMock()

    # Override the FastAPI app's dependencies
    app.dependency_overrides[settings] = override_get_settings
    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest.fixture(scope="function", autouse=False)
def unauthenticated_client(test_app: FastAPI) -> AsyncClient:
    """Build database and create unauthenticated test client."""
    print("unauthenticated_client")
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


@pytest.fixture(scope="function", autouse=False)
async def test_client(
    test_settings: TestSettings,
    test_db: AsyncSession,
    test_app: FastAPI,
) -> AsyncClient:
    """Build database and create authenticated test client."""
    print("test_client")
    hashed_password = auth_service.get_password_hash("123456")
    user = await UserFactory.create_(
        db=test_db, hashed_password=hashed_password, is_confirmed=True
    )
    access_token = auth_service.create_email_token(user, test_settings)
    headers = {"Authorization": f"Bearer {access_token}"}
    return AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers=headers,
    )


print("I'm in ", Path(__file__))
