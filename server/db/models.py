# models.py
from typing import Type, TypeVar
from sqlalchemy import JSON, Boolean, ForeignKey, create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import google.oauth2.credentials as oauth2_credentials
import server.db.database as database

Base = declarative_base()

class UserStatus(Base):
    __tablename__ = 'user_status'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # ForeignKey reference to GoogleUser's id
    status = Column(String)
    data = Column(JSON)
    user = relationship("GoogleUser", back_populates="status", uselist=False)  # uselist=False for one-to-one

T = TypeVar('T', bound='GoogleUser')
class GoogleUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String)
    name = Column(String)
    credentials = Column(String)
    status = relationship("UserStatus", back_populates="user", uselist=False)
    emails = relationship("GoogleEmail", back_populates="user")
    
    @classmethod
    def get_or_create(cls: Type[T], email: str, serialized_credentials: str) -> T:
        session = database.get_session()
        user = session.query(GoogleUser).filter_by(email=email).first()
        if user is None:
            user = GoogleUser(email=email, credentials=serialized_credentials)
            session.add(user)

            session.commit()
            status = UserStatus(user_id=user.id, status='created', data={})
            session.add(status)
            session.commit()
        return user 
    
class GoogleEmail(Base):
    __tablename__ = 'google_emails'
    id = Column(Integer, primary_key=True)
    gmail_id = Column(String)
    is_read = Column(Boolean)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("GoogleUser", back_populates="emails")

