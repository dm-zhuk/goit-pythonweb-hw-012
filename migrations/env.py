import logging
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, pool
from logging.config import fileConfig
from alembic import context
from src.database.models import Base
from src.services.base import Settings

project_root = (
    "/Users/macbook/Documents/GitHub/15_Fullstack_WebDevPython/goit-pythonweb-hw-012"
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger("alembic.env")
config = context.config
config_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
)
config.set_main_option("config_file_name", config_file)

if os.path.exists(config_file):
    fileConfig(config_file)
    logger.info(f"Loaded logging config from {config_file}")
else:
    logging.basicConfig(level=logging.INFO)
    logger.warning(f"Config file {config_file} not found")

settings = Settings()
db_name = "contacts_db_template" if "pytest" in sys.modules else "contacts_db"
db_url = (
    settings.DATABASE_URL.replace("asyncpg", "psycopg2")
    .replace("db:5432", "localhost:5432")
    .replace("contacts_db", db_name)
)
logger.info(f"Using database URL: {db_url}")
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
