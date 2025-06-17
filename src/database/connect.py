from redis.asyncio import StrictRedis
from redis_cache import RedisCache
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.services.base import settings

import logging

logger = logging.getLogger(__name__)


rc = StrictRedis(host="redis", port=6379, decode_responses=True)
cache = RedisCache(redis_client=rc)


engine = create_async_engine(settings.DATABASE_URL, echo=True)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


@cache.cache(limit=3600)
async def fetch_user(email: str, db: AsyncSession):
    from src.repository.users import get_user_by_email

    user = await get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as db:
        try:
            yield db
        except Exception as err:
            await db.rollback()
            logger.error(f"Database error: {str(err)}")
            raise
        finally:
            await db.close()
