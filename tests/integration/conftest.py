import asyncio
import pytest
import redis.asyncio as redis

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.db import get_db, Base
from src.services.base import settings

# ───────────────────────────────
# DB Setup
# ───────────────────────────────

test_engine = create_async_engine(settings.DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


# ───────────────────────────────
# Redis Setup
# ───────────────────────────────


@pytest.fixture(scope="session")
async def redis_client():
    rc = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
    )
    try:
        await rc.ping()
    except Exception as e:
        raise RuntimeError("Redis connection failed: ", e)
    await rc.flushdb()
    yield rc
    await rc.close()


# ───────────────────────────────
# Pytest Fixtures
# ───────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
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
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
