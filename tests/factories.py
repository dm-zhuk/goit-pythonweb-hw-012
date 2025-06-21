from datetime import datetime
from uuid import UUID

from factory.base import StubFactory
from factory.declarations import LazyFunction
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


fake = Faker()


class BaseFactory(StubFactory):
    @classmethod
    def build_dict(cls, **kwargs) -> dict:
        """Build a model dict from kwargs."""
        data = {}
        for key, value in cls.build(**kwargs).__dict__.items():
            if key == "_sa_instance_state":
                continue
            if isinstance(value, UUID):
                data[key] = str(value)
            else:
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


class UserFactory(BaseFactory):
    class Meta:
        model = User

    id = LazyFunction(lambda: fake.id())
    email = LazyFunction(lambda: fake.simple_profile().get("mail"))
