import enum
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
import sqlalchemy
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
    email_count = Column(Integer)
    deleted_emails = Column(Integer)
    to_be_deleted_emails = Column(Integer)


T = TypeVar("T", bound="GoogleUser")


DELETED_LABEL = "deleted_by_cleanmail2"


class GoogleUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    credentials = Column(String)

    # The label ID for the CleanMail label in the user's Gmail account
    cleanmail_label_id = Column(String)

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
        # Hit the cache first, but if no user shows up try an uncached query
        user = (
            session.query(GoogleUser).filter(GoogleUser.email == email).first()
            or session.query(GoogleUser)
            .filter(GoogleUser.email == email)
            .populate_existing()
            .first()
        )

        if user is None:
            user = GoogleUser(email=email, credentials=serialized_credentials)
            session.add(user)

            session.commit()
            status = UserStatus(user_id=user.id, status="created", data={})
            session.add(status)
        else:
            user.credentials = serialized_credentials

        if user.cleanmail_label_id is None:
            from cleanmail.gmail import api as gmail_api

            user.cleanmail_label_id = gmail_api.get_or_create_label_id(
                gmail_api.get_service(user.get_google_credentials()), DELETED_LABEL
            )

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


class GmailSenderAddress(Base):
    __tablename__ = "gmail_sender_address"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("GoogleUser", uselist=False)

    sender_id = Column(Integer, ForeignKey("gmail_sender.id"))
    sender = relationship("GmailSender", back_populates="addresses")

    email = Column(String)
    name = Column(String)
    email_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_gmail_sender_address_email", "user_id", "email"),
        Index("idx_gmail_sender_address_name", "user_id", "name"),
        Index("idx_gmail_sender_addresses_sender_id", "sender_id"),
    )


class SenderStatus(enum.Enum):
    NONE = "none"
    CLEAN = "clean"
    KEEP = "keep"
    LATER = "later"


class AddressStats:
    def __init__(self, address: str):
        self.address = address
        self.count = 0
        self.deleted = 0
        self.important = 0
        self.unread = 0
        self.replied = 0

    def read_fraction(self):
        return 1 - (self.unread * 1.0 / self.count)

    def replied_fraction(self):
        return self.replied * 1.0 / self.count

    def important_fraction(self):
        return self.important * 1.0 / self.count

    def is_personal_domain(self):
        domain = self.address.split("@")[1] if "@" in self.address else self.address
        return domain in _PERSONAL_DOMAINS

    def importance_score(self):
        return (
            ((self.read_fraction() + 0.01) ** 0.2)
            * ((self.replied_fraction() + 0.3) ** 2)
            * (self.important_fraction() + 0.02)
            * (20.0 if self.is_personal_domain() else 1.0)
        )

    def value_prop(self):
        sigmoid = 1 / (1 + math.exp(-self.importance_score() * 100))
        return (1 - sigmoid) * self.count

    def __repr__(self):
        return f"AddressStats({self.address}, {self.count}, {self.deleted}, {self.important}, {self.unread}, {self.replied}, {self.importance_score()})"


class GmailSender(Base):
    __tablename__ = "gmail_sender"
    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("GoogleUser", uselist=False)
    addresses = relationship("GmailSenderAddress", back_populates="sender")
    threads = relationship("GmailThread", back_populates="sender")

    emails_sent = Column(Integer)
    emails_unread = Column(Integer)
    emails_important = Column(Integer)
    emails_replied = Column(Integer)
    emails_deleted = Column(Integer)

    status = Column(sqlalchemy.Enum(SenderStatus), default=SenderStatus.NONE)
    last_cleaned = Column(DateTime)

    def get_primary_address(self) -> GmailSenderAddress:
        return max(self.addresses, key=lambda x: x.email_count)

    def read_fraction(self):
        return 1 - (self.emails_unread * 1.0 / self.emails_sent)

    def replied_fraction(self):
        return self.emails_replied * 1.0 / self.emails_sent

    def important_fraction(self):
        return self.emails_important * 1.0 / self.emails_sent

    def is_personal_domain(self):
        for address in self.addresses:
            domain = (
                address.email.split("@")[1] if "@" in address.email else address.email
            )
            if domain in _PERSONAL_DOMAINS:
                return True
        return False

    def importance_score(self):
        return (
            ((self.read_fraction() + 0.01) ** 0.5)
            * ((self.replied_fraction() + 0.3) ** 2)
            * self.important_fraction()
            * (8.0 if self.is_personal_domain() else 1.0)
        )

    def get_stats(self):
        stats = AddressStats(self.get_primary_address().email)
        stats.count = self.emails_sent
        stats.deleted = self.emails_deleted
        stats.important = self.emails_important
        stats.unread = self.emails_unread
        stats.replied = self.emails_replied
        return stats

    __table_args__ = (Index("idx_gmail_sender_user_id", "user_id"),)


class GmailThread(Base):
    __tablename__ = "gmail_thread"
    id = Column(Integer, primary_key=True)
    thread_id = Column(String)

    # True if any message in thread is read
    is_read = Column(Boolean)

    most_recent_date = Column(DateTime)

    sender_id = Column(Integer, ForeignKey("gmail_sender.id"))
    sender = relationship("GmailSender", back_populates="threads", uselist=False)

    sender_address_id = Column(Integer, ForeignKey("gmail_sender_address.id"))
    sender_address = relationship("GmailSenderAddress", uselist=False)

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
            "user_id",
            asc("most_recent_date"),
            "is_read",
        ),
        Index("idx_gmail_thread_sender", "user_id", "sender_id"),
    )
