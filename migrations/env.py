from logging.config import fileConfig
import logging
import os
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from src.database.connect import Base
from src.services.base import settings
import asyncio

logger = logging.getLogger("alembic.env")
config = context.config

config_file = config.config_file_name
if config_file is None:
    config_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    config.set_main_option("config_file_name", config_file)

try:
    logger.info(f"Attempting to load logging config from: {config_file}")
    if os.path.exists(config_file):
        fileConfig(config_file)
        logger.info(f"Successfully loaded logging config from {config_file}")
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warning(f"Config file {config_file} does not exist, using basic logging")
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    logger.warning(f"Failed to configure logging: {e}, using basic logging")

try:
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    logger.info(f"Using database URL (sync): {sync_url}")
    config.set_main_option("sqlalchemy.url", sync_url)
except AttributeError as e:
    logger.error(f"Failed to load DATABASE_URL: {e}")
    raise

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    logger.info("Running migrations in offline mode")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    logger.info(f"Connecting to database: {settings.DATABASE_URL}")
    try:
        connectable = create_async_engine(
            settings.DATABASE_URL,
            echo=True,
            poolclass=pool.NullPool,
        )
    except Exception as e:
        logger.error(f"Failed to create async engine: {e}")
        raise

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    try:
        asyncio.run(run_async_migrations())
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
