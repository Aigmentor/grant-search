import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.db.models import Base

DATABASE_URI = os.environ['POSTGRES_URL']

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session()