import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.main import app
from src.database.db import get_db, Base


class Settings(BaseSettings):
    DATABASE_URL: str
    model_config = SettingsConfigDict(env_file="/app/.env.test")


settings = Settings()
TEST_DATABASE_URL = settings.DATABASE_URL

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client():
    """
    An `AsyncClient` instance that can be used to make requests to the
    application.

    The client is set up to use the test database and overrides the
    `get_db` dependency to use the overridden `get_db` function.

    This fixture is scoped to each function, so each test will have
    a fresh instance of the client.

    Yields:
        AsyncClient: An instance of the `AsyncClient` that can be used to
            make requests to the application.
    """
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
