import datetime
import logging
from cleanmail.db.models import GmailSender, GmailThread, GoogleUser
from cleanmail.db.database import get_scoped_session, get_session
import cleanmail.gmail.api as gmail_api
from sqlalchemy import or_


def delete_thread(session, service, thread, label_id):
    if thread.deleted:
        logging.info(f"Thread {thread.thread_id} already deleted")
        return
    logging.info(f"Deleting thread: {thread.thread_id}")
    gmail_api.add_label(service, thread.thread_id, label_id)
    # gmail_api.delete_thread(service, thread.thread_id)
    thread.deleted = True
    session.commit()


def delete_sender(user_id: int, sender_id: int):
    try:
        logging.info(f"Starting deleting sender: {sender_id} for {user_id}")
        session = get_session()
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
                GmailThread.sender == sender_id,
                GmailThread.most_recent_date < stop_date,
                GmailThread.has_replied == False,
                or_(GmailThread.deleted.is_(None), GmailThread.deleted == False),
            )
            .order_by(GmailThread.most_recent_date)
            .all()
        )

        logging.info(f"Deleting {len(threads)} threads for sender {sender.email}")
        service = gmail_api.get_service(credentials=user.get_google_credentials())
        label_id = gmail_api.get_or_create_label_id(service, "deleted_by_cleanmail")
        for thread in threads:
            delete_thread(session, service, thread, label_id)
        logging.info(f"Done deleting threads for {sender.email}")
    except Exception as e:
        logging.exception(f"Error deleting sender {sender_id}: {e}")
