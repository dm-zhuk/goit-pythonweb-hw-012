import logging
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, pool
from logging.config import fileConfig
from alembic import context


project_root = (
    "/Users/macbook/Documents/GitHub/15_Fullstack_WebDevPython/goit-pythonweb-hw-012"
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
logging.debug(f"sys.path: {sys.path}")

try:
    from src.database.models import Base
    from src.services.base import Settings
except ImportError as e:
    logging.error(f"Import failed: {e}")
    raise

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

settings = Settings()
db_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
).replace("db:5432", "localhost:5432")
logger.info(f"Using database URL: {db_url}")
config.set_main_option("sqlalchemy.url", db_url)

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


def run_migrations_online() -> None:
    logger.info(f"Connecting to database: {db_url}")
    try:
        connectable = create_engine(
            db_url,
            poolclass=pool.NullPool,
        )
    except Exception as e:
        logger.error(f"Failed to create engine: {e}")
        raise
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
