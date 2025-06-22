from redis.asyncio import StrictRedis
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.services.base import settings

import logging
import json

logger = logging.getLogger(__name__)

rc = StrictRedis(host="redis", port=6379, decode_responses=True)
logger.info(f"rc in db.py: {rc}")

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
    """
    Fetches a user by email address from the database.

    Args:
        email: The email address of the user to find.
        db: The database session to use.

    Returns:
        The user if found, or raises an HTTPException with a 404
            status code if not.

    Raises:
        HTTPException: If the user is not found.
    """
    from src.repository.users import get_user_by_email

    user = await get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


async def get_user_from_cache(email: str, db: AsyncSession) -> dict:
    """
    Fetches a user by email address from the cache.

    Args:
        email: The email address of the user to find.
        db: The database session to use.

    Returns:
        The user if found in the cache, or the user from the database
            if not found in the cache.

    Raises:
        HTTPException: If the user is not found in the cache or database.
    """
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
        )  # 'setex' sets a key to a value with a mandatory expiration time in seconds

    except Exception as e:
        logger.error(f"Failed to cache user {email}: {str(e)}")

    return user_dict


async def init_db():
    """
    Initialize the database.

    This function creates all tables defined in the SQLAlchemy ORM models.
    It establishes a connection to the database and executes the schema
    creation commands.

    Raises:
        Exception: If there's an error during the table creation process.
    """

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    Dependency function to provide a database session.

    This function is designed to be used with FastAPI's dependency injection
    system to provide an asynchronous SQLAlchemy database session. It ensures
    that the session is properly initialized, committed, or rolled back in case
    of errors, and closed after use.

    Yields:
        AsyncSession: An active database session.

    Raises:
        Exception: If any error occurs during the database operations, it logs
        the error and raises the exception after rolling back the transaction.
    """

    async with async_session() as db:
        try:
            yield db
        except Exception as err:
            await db.rollback()
            logger.error(f"Database error: {str(err)}")
            raise
        finally:
            await db.close()
