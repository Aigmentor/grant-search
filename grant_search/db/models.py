import enum
from typing import Type, TypeVar
from sqlalchemy import (
    ARRAY,
    JSON,
    DDL,
    VARCHAR,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
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
from sqlalchemy.orm import relationship, mapped_column, Mapped, deferred
from sqlalchemy.orm import declarative_mixin
from datetime import datetime

from pgvector.sqlalchemy import Vector

import grant_search.db.database as database

Base = declarative_base()


def init_db():
    create_vector_extension = DDL("CREATE EXTENSION IF NOT EXISTS vector")
    event.listen(Base.metadata, "before_create", create_vector_extension)
    Base.metadata.create_all(database.engine)


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_modified = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Agency(Base):
    __tablename__ = "agencies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # One-to-many relationship with data sources
    data_sources = relationship("DataSource", back_populates="agency")


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    timestamp = Column(DateTime)
    origin = Column(String)

    # Add foreign key to Agency
    agency_id = Column(Integer, ForeignKey("agencies.id"))
    # Add relationship back to Agency
    agency = relationship("Agency", back_populates="data_sources")

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
    award_id = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    amount = Column(Float)
    title = Column(String)
    description = Column(String)

    # Foreign key to DataSource
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    data_source = relationship("DataSource", back_populates="grants")

    # Many-to-many relationship with grantees
    grantees = relationship(
        "Grantee", secondary="grant_grantee", back_populates="grants"
    )
    raw_text = deferred(Column(LargeBinary))

    # Update the relationship to include cascade delete
    derived_data = relationship(
        "GrantDerivedData", back_populates="grant", cascade="all, delete-orphan"
    )

    embeddings = relationship(
        "GrantEmbedding", back_populates="grant", cascade="all, delete-orphan"
    )

    def get_award_url(self):
        if self.data_source.agency.name == "NSF":
            return f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={self.award_id}&HistoricalAwards=false"
        elif self.data_source.agency.name == "NIH":
            return f"https://reporter.nih.gov/project-details/{self.award_id}"
        else:
            return None


class DEIStatus(enum.Enum):
    NONE = "none"
    MENTIONS_DEI = "mentions_dei"
    PARTIAL_DEI = "partial_dei"
    PRIMARILY_DEI = "primarily_dei"


class GrantDerivedData(Base):
    __tablename__ = "grant_derived_data"
    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey("grants.id", ondelete="CASCADE"))
    dei_status = Column(Enum(DEIStatus))
    dei_women = Column(Boolean)
    dei_race = Column(Boolean)
    outrageous = Column(Boolean)
    primary_dei = Column(Boolean)
    hard_science = Column(Boolean)
    political_science = Column(Boolean)
    carbon = Column(Boolean)

    grant = relationship("Grant", back_populates="derived_data")


class GrantEmbedding(Base):
    __tablename__ = "grant_embedding"
    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey("grants.id", ondelete="CASCADE"))
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)

    grant = relationship("Grant", back_populates="embeddings")

    __table_args__ = (
        Index(
            "idx_grant_embedding_user_id",
            "grant_id",
        ),
    )


# Add this association table before the GrantSearchQuery class
grant_search_query_grants = Table(
    "grant_search_query_grants",
    Base.metadata,
    Column("grant_search_query_id", Integer, ForeignKey("grant_search_queries.id")),
    Column("grant_id", Integer, ForeignKey("grants.id")),
)


class GrantSearchQuery(TimestampMixin, Base):
    __tablename__ = "grant_search_queries"
    id = Column(Integer, primary_key=True)
    query = Column(String)
    timestamp = Column(DateTime)
    query_text = Column(String)
    grants = relationship("Grant", secondary="grant_search_query_grants")
    reasons = Column(ARRAY(String))
    complete = Column(Boolean)
    sampling_fraction = Column(Float)
    status = Column(String)
