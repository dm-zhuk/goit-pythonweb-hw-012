import warnings
import asyncio
import pytest_asyncio
import redis.asyncio as redis

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.db import get_db, Base
from src.services.base import settings

warnings.simplefilter("always", RuntimeWarning)

# ───────────────────────────────
# Database Setup
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


@pytest_asyncio.fixture(scope="session")
async def redis_client():
    rc = redis.StrictRedis(
        host="redis_test",
        port=6379,
        decode_responses=True,
    )
    try:
        pong = await rc.ping()
        assert pong is True
    except Exception as e:
        raise RuntimeError(f"Redis not available at startup: {e}")
    yield rc
    try:
        await rc.flushdb()
        await rc.close()
    except Exception as e:
        print(f"⚠️ Redis teardown warning: {e}")


# ───────────────────────────────
# Event Loop
# ───────────────────────────────


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


# ───────────────────────────────
# Test DB Lifecycle
# ───────────────────────────────


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ───────────────────────────────
# Per-Test Fixtures
# ───────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
