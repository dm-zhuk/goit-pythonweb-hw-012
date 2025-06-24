# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from src.database.models import Base
from src.services.base import Settings


def init_db():
    settings = Settings()
    db_url = (
        settings.DATABASE_URL.replace("asyncpg", "psycopg2")
        .replace("db:5432", "localhost:5432")
        .replace("contacts_db", "contacts_db_template")
    )
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    engine.dispose()


if __name__ == "__main__":
    init_db()
