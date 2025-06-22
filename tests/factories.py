import pytest

from fastapi import FastAPI
from redis.asyncio import Redis
from datetime import datetime
from factory.base import StubFactory
from factory.declarations import LazyFunction
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from tests.conftest import TestSettings
from src.database.models import User, Role
from src.services.auth import auth_service
from src.repository.users import get_user_by_email

fake = Faker()


class BaseFactory(StubFactory):
    @classmethod
    def build_dict(cls, **kwargs) -> dict:
        """Build a model dict from kwargs."""
        data = {}
        for key, value in cls.build(**kwargs).__dict__.items():
            if key == "_sa_instance_state":
                continue
            data[key] = value
        return data

    @classmethod
    async def create_(
        cls,
        db: AsyncSession,
        **kwargs,
    ):
        """Async version of create method."""
        fields = cls.build_dict(**kwargs)
        for key, value in fields.items():
            if isinstance(value, datetime):
                fields[key] = value.replace(tzinfo=None)
        obj = cls._meta.model(**fields)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str):
        """Fetch user by email using repository."""
        return await get_user_by_email(email, db)


class UserFactory(BaseFactory):
    class Meta:
        model = User

    id = LazyFunction(lambda: fake.pyint(min_value=1, max_value=100))
    email = LazyFunction(lambda: fake.simple_profile().get("mail"))
    hashed_password = LazyFunction(
        lambda: auth_service.get_password_hash("password123")
    )
    is_verified = False
    avatar_url = None
    roles = Role.user.value


# ... (keep your existing imports and other fixtures)


@pytest.fixture(scope="function")
async def test_cache(test_settings: TestSettings) -> Redis:
    """Provide test Redis client."""
    redis_client = Redis.from_url(test_settings.REDIS_URI, decode_responses=True)
    await redis_client.flushdb()  # Clear before test
    yield redis_client
    await redis_client.flushdb()  # Clear after test
    await redis_client.close()


@pytest.fixture(scope="function")
async def test_client(
    test_db: AsyncSession, test_app: FastAPI, test_settings: TestSettings
) -> AsyncClient:
    """Authenticated test client."""
    hashed_password = auth_service.get_password_hash("password123")
    user = await UserFactory.create_(
        db=test_db,
        email="test@example.com",
        hashed_password=hashed_password,
        is_verified=True,  # For authenticated routes
        roles=Role.user.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    return AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers=headers,
    )
