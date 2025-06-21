from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata_ = MetaData()


class MinimalBase(DeclarativeBase):
    __abstract__ = True
    metadata = metadata_


class IDOrmModel(MinimalBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
