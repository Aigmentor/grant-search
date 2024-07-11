from concurrent.futures import ThreadPoolExecutor
import logging
from sqlalchemy import or_
from sqlalchemy.orm import Session

from cleanmail.db.database import get_scoped_session
from cleanmail.db.models import GmailSender, GmailThread, GoogleUser, SenderStatus


def compute_user_status(session: Session, user: GoogleUser):
    status_json = user.status.data
    deleted_count = (
        session.query(GmailThread)
        .filter(GmailThread.user_id == user.id, GmailThread.deleted == True)
        .count()
    )
    user.status.deleted_emails = deleted_count
    user.status.email_count = (
        session.query(GmailThread).filter(GmailThread.user_id == user.id).count()
    )
    user.status.to_be_deleted_emails = (
        session.query(GmailThread)
        .join(GmailSender)
        .filter(
            GmailThread.user_id == user.id,
            GmailSender.user_id == user.id,
            GmailSender.status == SenderStatus.CLEAN,
            GmailThread.deleted == False,
        )
        .count()
    )
    session.commit()


def compute_stats_for_sender(session: Session, sender_id: int):
    # Load the sender with the new session
    sender = session.get(GmailSender, sender_id)
    # Reset address email counts to 0
    addresses = sender.addresses
    for address in addresses:
        address.email_count = 0
    threads = (
        session.query(GmailThread)
        .filter(
            GmailThread.user_id == sender.user_id,
            GmailThread.sender_id == sender.id,
            or_(GmailThread.deleted.is_(None), GmailThread.deleted == False),
        )
        .all()
    )
    email_count = len(threads)
    # Senders can have 0 threads if all their emails were deleted
    if email_count == 0:
        return
    replied = 0
    unread = 0
    important = 0
    deleted = 0
    for thread in threads:
        if thread.has_replied:
            replied += 1
        if not thread.is_read:
            unread += 1
        if "IMPORTANT" in thread.labels:
            important += 1
        if thread.deleted:
            deleted += 1

        thread.sender_address.email_count += 1

    sender.emails_sent = email_count
    sender.emails_important = important
    sender.emails_replied = replied
    sender.emails_unread = unread
    sender.emails_deleted = deleted
    session.commit()


def compute_stats(session: Session, user: GoogleUser):
    logging.info(f"Computing stats for {user.email}")
    senders = session.query(GmailSender).filter(GmailSender.user_id == user.id).all()

    with ThreadPoolExecutor(max_workers=6) as executor:
        executor.map(
            lambda sender: compute_stats_for_sender(get_scoped_session(), sender.id),
            senders,
        )
