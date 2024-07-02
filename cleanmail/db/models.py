import math
from typing import Type, TypeVar
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    asc,
    Column,
    Integer,
    String,
    desc,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.mutable import MutableDict

import cleanmail.db.database as database
import cleanmail.web.oauth as oauth

Base = declarative_base()


def init_db():
    Base.metadata.create_all(database.engine)


class UserStatus(Base):
    __tablename__ = "user_status"
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id")
    )  # ForeignKey reference to GoogleUser's id
    status = Column(String)
    data = Column(MutableDict.as_mutable(JSON))
    user = relationship(
        "GoogleUser", back_populates="status", uselist=False
    )  # uselist=False for one-to-one
    is_cleaning = Column(Boolean)
    cleaning_start = Column(DateTime)


T = TypeVar("T", bound="GoogleUser")


class GoogleUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    credentials = Column(String)
    status = relationship("UserStatus", back_populates="user", uselist=False)
    threads = relationship("GmailThread", back_populates="user")
    senders = relationship("GmailSender", back_populates="user")
    total_email_count = Column(Integer)

    __table_args__ = (Index("idx_google_user_email", email),)

    def get_google_credentials(self):
        return oauth.deserialize_credentials(self.credentials)

    @classmethod
    def get_or_create(
        cls: Type[T], session: Session, email: str, serialized_credentials: str
    ) -> T:
        email = email.lower().strip()
        user = session.query(GoogleUser).filter(GoogleUser.email == email).first()
        if user is None:
            user = GoogleUser(email=email, credentials=serialized_credentials)
            session.add(user)

            session.commit()
            status = UserStatus(user_id=user.id, status="created", data={})
            session.add(status)
        else:
            user.credentials = serialized_credentials
        session.commit()
        return user


_PERSONAL_DOMAINS = set(
    [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "msn.com",
        "icloud.com",
    ]
)


class GmailSender(Base):
    __tablename__ = "gmail_sender"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("GoogleUser", back_populates="senders")

    email = Column(String)
    name = Column(String)
    emails_sent = Column(Integer)
    emails_unread = Column(Integer)
    emails_important = Column(Integer)
    emails_replied = Column(Integer)
    emails_deleted = Column(Integer)

    should_be_cleaned = Column(Boolean)
    last_cleaned = Column(DateTime)

    def read_fraction(self):
        return 1 - (self.emails_unread * 1.0 / self.emails_sent)

    def replied_fraction(self):
        return self.emails_replied * 1.0 / self.emails_sent

    def important_fraction(self):
        return self.emails_important * 1.0 / self.emails_sent

    def is_personal_domain(self):
        domain = self.email.split("@")[1] if "@" in self.email else self.email
        return domain in _PERSONAL_DOMAINS

    def importance_score(self):
        return (
            ((self.read_fraction() + 0.01) ** 0.5)
            * ((self.replied_fraction() + 0.3) ** 2)
            * self.important_fraction()
            * (8.0 if self.is_personal_domain() else 1.0)
        )

    def value_prop(self):
        sigmoid = 1 / (1 + math.exp(-self.importance_score() * 100))
        return (1 - sigmoid) * self.emails_sent

    __table_args__ = (Index("idx_gmail_sender_email", user_id, email),)


class GmailThread(Base):
    __tablename__ = "gmail_thread"
    id = Column(Integer, primary_key=True)
    thread_id = Column(String)

    # True if any message in thread is read
    is_read = Column(Boolean)

    most_recent_date = Column(DateTime)
    sender = Column(Integer, ForeignKey("gmail_sender.id"))

    # True if user has replied to any messages
    has_replied = Column(Boolean)

    # Indicates only 1 message in "thread" (i.e. not a thread)
    is_singleton = Column(Boolean)

    is_important = Column(Boolean)
    # Commas separated list of all labels on thead
    labels = Column(String)

    deleted = Column(Boolean)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("GoogleUser", back_populates="threads")

    __table_args__ = (
        Index(
            "idx_gmail_thread_most_recent_is_read",
            user_id,
            asc("most_recent_date"),
            "is_read",
        ),
        Index("idx_gmail_thread_sender", user_id, sender),
    )
