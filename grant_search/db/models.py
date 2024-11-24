from typing import Type, TypeVar
from sqlalchemy import (
    JSON,
    DDL,
    VARCHAR,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    TypeDecorator,
    asc,
    Column,
    Integer,
    String,
    Float,
    desc,
    Table,
    event,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, mapped_column, Mapped

from pgvector.sqlalchemy import Vector

import grant_search.db.database as database

Base = declarative_base()


def init_db():
    create_vector_extension = DDL("CREATE EXTENSION IF NOT EXISTS vector")
    event.listen(Base.metadata, "before_create", create_vector_extension)
    Base.metadata.create_all(database.engine)


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    timestamp = Column(DateTime)
    origin = Column(String)

    # Relationship to grants
    grants = relationship("Grant", back_populates="data_source")


class Grantee(Base):
    __tablename__ = "grantees"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # Many-to-many relationship with grants
    grants = relationship("Grant", secondary="grant_grantee", back_populates="grantees")


# Association table for the many-to-many relationship between Grant and Grantee
grant_grantee = Table(
    "grant_grantee",
    Base.metadata,
    Column("grant_id", Integer, ForeignKey("grants.id")),
    Column("grantee_id", Integer, ForeignKey("grantees.id")),
)


class Grant(Base):
    __tablename__ = "grants"
    id = Column(Integer, primary_key=True)
    start_year = Column(Integer)
    end_year = Column(Integer)
    amount = Column(Float)
    description = Column(String)

    # Foreign key to DataSource
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    data_source = relationship("DataSource", back_populates="grants")

    # Many-to-many relationship with grantees
    grantees = relationship(
        "Grantee", secondary="grant_grantee", back_populates="grants"
    )


class GrantEmbedding(Base):
    __tablename__ = "grant_embedding"
    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey("grants.id"))
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    __table_args__ = (
        Index(
            "idx_grant_embedding_user_id",
            "grant_id",
        ),
    )
