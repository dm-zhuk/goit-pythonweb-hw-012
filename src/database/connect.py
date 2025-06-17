from redis.asyncio import StrictRedis
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.services.base import settings

import logging
import json

logger = logging.getLogger(__name__)

rc = StrictRedis(host="redis", port=6379, decode_responses=True)

engine = create_async_engine(settings.DATABASE_URL, echo=True)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_user_from_db(email: str, db: AsyncSession) -> dict:
    from src.repository.users import get_user_by_email

    user = await get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


async def get_user_from_cache(email: str, db: AsyncSession) -> dict:
    cache_key = f"get_user_from_cache:{email}"
    cached_user = await rc.get(cache_key)
    if cached_user:
        try:
            return json.loads(cached_user)
        except json.JSONDecodeError:
            logger.warning(f"Invalid cached data for key {cache_key}")
    user_dict = await get_user_from_db(email, db)
    try:
        await rc.setex(
            cache_key, 3600, json.dumps(user_dict)
        )  # Sets a key to a value with a mandatory expiration time in seconds

    except Exception as e:
        logger.error(f"Failed to cache user {email}: {str(e)}")

    return user_dict


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
