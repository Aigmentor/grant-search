import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URI = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
# .
engine = create_engine(DATABASE_URI, pool_size=12, max_overflow=20, pool_recycle=120)
Session = sessionmaker(bind=engine)

ScopedSession = scoped_session(Session)


def get_session():
    return Session()


def get_scoped_session():
    return ScopedSession()
