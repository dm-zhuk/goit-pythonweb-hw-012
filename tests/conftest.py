import pytest
import logging
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

from src.main import app
from src.database.models import Base, User
from src.database.db import get_db
from src.services.auth import auth_service

logger = logging.getLogger(__name__)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_user = {
    "email": "pool@example.com",
    "password": "12345678",
}


@pytest.fixture(scope="module", autouse=True)
async def init_models_wrap():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Create a test user only if it doesn't already exist
        existing_user = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        if not existing_user.scalar_one_or_none():
            hashed_password = auth_service.get_password_hash(test_user["password"])
            current_user = User(
                email=test_user["email"],
                hashed_password=hashed_password,
                is_verified=True,
                avatar_url="<https://twitter.com/gravatar>",
            )
            session.add(current_user)
            await session.commit()


@pytest.fixture(scope="module")
def client():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


@pytest_asyncio.fixture()
async def get_token():
    token = await auth_service.create_email_token(data={"sub": test_user["email"]})
    return token
