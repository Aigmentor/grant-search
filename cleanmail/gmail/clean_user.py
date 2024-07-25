from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
from typing import List
from cleanmail.db.models import (
    DELETED_LABEL,
    GmailSender,
    GmailThread,
    GoogleUser,
    SenderStatus,
)
from cleanmail.db.database import get_scoped_session, get_scoped_session, get_session
import cleanmail.gmail.api as gmail_api
from sqlalchemy import or_

from cleanmail.gmail.stats import compute_stats

_MAX_CLEAN_THREADS = 8


def delete_thread(session, service, thread, label_id):
    if thread.deleted:
        logging.info(f"Thread {thread.thread_id} already deleted")
        return
    logging.info(f"Deleting thread: {thread.thread_id}")

    gmail_api.exec_with_rate_limit(
        gmail_api.add_label, service, thread.thread_id, label_id
    )
    thread.deleted = True
    session.commit()


def clean_sender(user_id: int, sender_id: int):
    try:
        logging.info(f"Starting deleting sender: {sender_id} for {user_id}")
        session = get_scoped_session()
        user = session.get(GoogleUser, user_id)
        if user is None:
            logging.error(f"User {user_id} not found")
            return

        sender = session.get(GmailSender, sender_id)
        if sender is None:
            logging.error(f"Sender {sender_id} not found")
            return

        if sender.user_id != user_id:
            logging.error(f"User {user_id} cannot delete sender {sender_id}")
            return

        stop_date = datetime.datetime.now() - datetime.timedelta(days=90)
        threads = (
            session.query(GmailThread)
            .filter(
                GmailThread.user_id == user_id,
                GmailThread.sender_id == sender_id,
                GmailThread.most_recent_date < stop_date,
                GmailThread.has_replied == False,
                or_(GmailThread.deleted.is_(None), GmailThread.deleted == False),
            )
            .order_by(GmailThread.most_recent_date)
            .all()
        )

        logging.info(f"Deleting {len(threads)} threads for sender {sender.addresses}")
        service = gmail_api.get_service(credentials=user.get_google_credentials())
        label_id = user.cleanmail_label_id
        assert label_id is not None
        for i, thread in enumerate(threads):
            delete_thread(session, service, thread, label_id)
            if i % 100 == 99:
                logging.info(f"Deleted {i+1} threads for {sender.addresses[0].email}")
        sender.last_cleaned = datetime.datetime.now()
        session.commit()
        logging.info(f"Done deleting threads for {sender.addresses}")
    except Exception as e:
        logging.exception(f"Error deleting sender {sender_id}: {e}")


def clean_email_for_user(user_id: int):
    with get_session() as session:
        user = session.get(GoogleUser, user_id)
        if user is None:
            logging.error(f"User {user_id} not found")
            return

        status = user.status
        if (
            status.is_cleaning
            and status.cleaning_start
            > datetime.datetime.now() - datetime.timedelta(seconds=7200)
        ):
            logging.error(f"User {user.email} is being cleaned already")
            return
        status.is_cleaning = True
        status.cleaning_start = datetime.datetime.now()
        session.commit()
        old_senders = []
        try:
            while True:
                logging.info(f"Cleaning email for user {user.email}")
                senders = (
                    session.query(GmailSender)
                    .filter(
                        GmailSender.user_id == user_id,
                        GmailSender.status == SenderStatus.CLEAN,
                    )
                    .all()
                )
                new_senders = [item for item in senders if item.id not in old_senders]
                if len(new_senders) == 0:
                    break

                with ThreadPoolExecutor(max_workers=_MAX_CLEAN_THREADS) as executor:
                    executor.map(
                        lambda sender: clean_sender(user_id, sender.id), new_senders
                    )
        finally:
            new_session = get_session()
            new_user = session.get(GoogleUser, user_id)
            new_user.status.is_cleaning = False
            status_json = new_user.status.data
            deleted_count = (
                session.query(GmailThread)
                .filter(GmailThread.user_id == user_id, GmailThread.deleted == True)
                .count()
            )
            status_json["deleted_emails"] = deleted_count
            new_session.commit()

        logging.info(f"Finished cleaning email for user {user.email}")
        compute_stats(session, user)
