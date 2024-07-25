from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import traceback
from sqlalchemy import or_
from sqlalchemy.orm import Session

from cleanmail.db.database import get_scoped_session
from cleanmail.db.models import (
    AddressStats,
    GmailSender,
    GmailThread,
    GoogleUser,
    SenderStatus,
)


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
    try:
        # Load the sender with the new session
        stats_by_address = dict()
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
            logging.warning(f"Sender {sender.get_primary_address()} has no threads")
            return

        for thread in threads:
            stats = stats_by_address.get(thread.sender_address_id)
            if stats is None:
                stats = AddressStats(thread.sender_address.email)
                stats_by_address[thread.sender_address_id] = stats
            stats.count += 1
            if thread.has_replied:
                stats.replied += 1
            if not thread.is_read:
                stats.unread += 1
            if "IMPORTANT" in thread.labels:
                stats.important += 1
            if thread.deleted:
                stats.deleted += 1

        sender.emails_sent = sum([stat.count for stat in stats_by_address.values()])
        sender.emails_important = sum(
            [stat.important for stat in stats_by_address.values()]
        )
        sender.emails_replied = sum(
            [stat.replied for stat in stats_by_address.values()]
        )
        sender.emails_unread = sum([stat.unread for stat in stats_by_address.values()])
        sender.emails_deleted = sum(
            [stat.deleted for stat in stats_by_address.values()]
        )

        session.commit()

        # Check if we should automatically split any items
        top_level_importance = sender.get_stats().importance_score()
        if top_level_importance < 0.0001:
            logging.warning(f"scores: {sender.get_stats()}")
        if len(addresses) > 1:
            for address in addresses:
                stats = stats_by_address[address.id]
                importance = stats.importance_score()
                if importance > 1 and importance > top_level_importance * 5:
                    logging.warning(
                        f"splitting {address.email}: {importance} vs {top_level_importance}"
                    )
                    from cleanmail.gmail.scan import split_address

                    split_address(session, address, SenderStatus.NONE)
                    # Return immediately, because split_address will call compute_stats again
                    return
    except Exception as e:
        logging.error(f"Error computing stats for sender {sender_id}: {e}")
        traceback.print_exc()


def compute_stats(session: Session, user: GoogleUser):
    logging.info(f"Computing stats for {user.email}")
    start_time = datetime.now()
    senders = session.query(GmailSender).filter(GmailSender.user_id == user.id).all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(
            lambda sender: compute_stats_for_sender(get_scoped_session(), sender.id),
            senders,
        )
    logging.info(
        f"Done computes stats for {user.email} in {datetime.now() - start_time}"
    )
