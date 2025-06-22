import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis
from src.database.models import Role
from src.services.auth import auth_service
from tests.factories import UserFactory
from tests.conftest import TestSettings
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from src.database.metadata import metadata_
import asyncio


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    return TestSettings()


@pytest.fixture(scope="session")
async def test_db():
    """Provide test database session with testcontainers."""
    postgres = PostgresContainer(
        image="postgres:16",
        username="testuser",
        password="testpass",
        dbname="testdb",
        port=5432,
        driver="asyncpg",
    )
    with postgres:
        connection_url = postgres.get_connection_url().replace("?sslmode=disable", "")
        print(f"PostgreSQL connection URL: {connection_url}")
        engine = create_async_engine(connection_url)
        async with engine.begin() as conn:
            await conn.run_sync(metadata_.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Ensure DB is ready
            for _ in range(10):
                try:
                    await session.execute("SELECT 1")
                    break
                except Exception:
                    await asyncio.sleep(1)
            else:
                raise RuntimeError("PostgreSQL container not ready")
            yield session
        async with engine.begin() as conn:
            await conn.run_sync(metadata_.drop_all)
        await engine.dispose()


@pytest.fixture(scope="function")
async def test_cache():
    """Provide test Redis client with testcontainers."""
    redis = RedisContainer(image="redis:7")
    with redis:
        redis_client = Redis.from_url(redis.get_connection_url(), decode_responses=True)
        print(f"Redis connection URL: {redis.get_connection_url()}")
        await redis_client.flushdb()
        yield redis_client
        await redis_client.flushdb()
        await redis_client.close()


@pytest.fixture(scope="session")
def test_app():
    """FastAPI app with mocked dependencies."""
    from src.main import app
    from src.database.db import get_db, init_db
    from fastapi.security import OAuth2PasswordBearer

    with patch("src.main.init_db", AsyncMock()):
        app.dependency_overrides[get_db] = lambda: None
        app.dependency_overrides[auth_service.oauth2_scheme] = (
            lambda: OAuth2PasswordBearer(tokenUrl="/api/users/login")
        )
        yield app
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_client(
    test_db: AsyncSession, test_app: FastAPI, test_settings: TestSettings
):
    """Authenticated test client."""
    hashed_password = auth_service.get_password_hash("password123")
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=hashed_password,
        is_verified=True,
        roles=Role.user.value,
    )
    test_app.dependency_overrides[test_app.dependency_overrides.get("get_db")] = (
        lambda: test_db
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers=headers,
    ) as client:
        yield client
