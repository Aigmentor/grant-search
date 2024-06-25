from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
import random
import re
import threading
from cleanmail.db.database import get_scoped_session
from cleanmail.db.models import GmailSender, GoogleUser, GmailThread
from cleanmail.gmail import api as gmail_api
from sqlalchemy.orm import Session

MAX_PROCESS_EMAIL_THREADS = 5

sender_lock = threading.Lock()


def _process_message(user: GoogleUser, message: dict):
    session = get_scoped_session()
    thread_id = message["id"]
    labels = set()
    max_date = None
    thread_size = len(message["messages"])
    from_email = None
    name = None
    for message in message["messages"]:
        if "labelIds" not in message:
            logging.warn(f"Skipping message without labelIds: {message}")
            continue
        for label in message["labelIds"]:
            labels.add(label)
        headers = message["payload"]["headers"]
        pattern = r"(?:(?P<name>.+?)\s+)?(?:<(?P<email>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)>)|(?P<email_only>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)"
        for header in headers:
            if header["name"] == "From":
                if from_email is None:
                    # Only use the sender on first email in thread
                    header_line = header["value"]
                    match = re.search(pattern, header_line)
                    if match:
                        from_email = match.group("email") or match.group("email_only")
                        name = match.group("name") or from_email
                        # print(
                        #     f"parsed {header_line} to name: '{name}', email: '{from_email}'"
                        # )
                    else:
                        print(f"Failed to match: {headers}")

        date = int(message["internalDate"])
        if max_date is None or date > max_date:
            max_date = date

    if name is None:
        print("Failed to find From header in: {headers}")
        return

    if max_date is not None:
        max_date = datetime.datetime.fromtimestamp(max_date / 1000)

    replied = "SENT" in labels
    is_unread = "UNREAD" in labels
    is_important = "IMPORTANT" in labels
    # logging.info(
    #     f"unread: {is_unread} important: {is_important} size: {thread_size} replied: {replied } from: {from_email} date: {max_date}"
    # )
    thread = session.query(GmailThread).filter_by(thread_id=thread_id).first()
    if thread is not None:
        pass
    else:
        sender = (
            session.query(GmailSender)
            .filter_by(user_id=user.id, email=from_email)
            .first()
        )
        if sender is None:
            # Grab the lock, check again for sender, then create if necessary
            with sender_lock:
                sender = (
                    session.query(GmailSender)
                    .filter_by(user_id=user.id, email=from_email)
                    .first()
                )
                if sender is None:
                    print(f"Creating new sender: {name} {from_email}")
                    sender = GmailSender(user_id=user.id, name=name, email=from_email)
                    session.add(sender)
                    session.commit()

        thread = GmailThread(
            thread_id=thread_id,
            user_id=user.id,
            is_read=not is_unread,
            sender=sender.id,
            has_replied=replied,
            is_singleton=thread_size == 1,
            is_important=is_important,
            most_recent_date=max_date,
            labels=",".join(labels),
        )
        session.add(thread)
        session.commit()
    return thread


def scan(session: Session, user: GoogleUser, max_items: int = 1000):
    # First check what we've already scanned
    count = session.query(GmailThread).filter_by(user_id=user.id).count()
    logging.info(f"Already scanned {count} emails for user {user.email}")

    oldest_email = (
        session.query(GmailThread)
        .filter_by(user_id=user.id)
        .order_by(GmailThread.most_recent_date)
        .first()
    )
    if oldest_email:
        oldest_email_date = oldest_email.most_recent_date
    else:
        oldest_email_date = datetime.datetime.now()
    logging.info(f"Oldest email: {oldest_email_date}")

    max = max_items - count
    if max <= 0:
        logging.info(f"Already scanned {count} emails for user {user.email}")
        return

    # Scan 50x as many emails, then subsample.
    message_ids = gmail_api.list_thread_ids_by_query(
        user.get_google_credentials(),
        "before:" + oldest_email_date.strftime("%Y/%m/%d"),
        max * 50,
    )
    if len(message_ids) > max:
        message_ids = random.sample(message_ids, max)
    print(f"message_ids {len(message_ids)} max: {max}")
    messages = gmail_api.list_messages_by_gthread_id(
        user.get_google_credentials(), message_ids, max_items=max
    )

    with ThreadPoolExecutor(max_workers=MAX_PROCESS_EMAIL_THREADS) as executor:
        results = executor.map(lambda msg: _process_message(user, msg), messages)

    for message in messages:
        _process_message(user, message)
    return messages


def compute_sender_stats(session: Session, user: GoogleUser):
    senders = session.query(GmailSender).filter_by(user_id=user.id).all()
    senders_with_stats = []
    for sender in senders:
        threads = (
            session.query(GmailThread)
            .filter_by(user_id=user.id, sender=sender.id)
            .all()
        )
        email_count = len(threads)
        # Senders can have 0 threads if all their emails were deleted
        if email_count == 0:
            continue
        replied = 0
        unread = 0
        important = 0
        for thread in threads:
            if thread.has_replied:
                replied += 1
            if not thread.is_read:
                unread += 1
            if "IMPORTANT" in thread.labels:
                important += 1
        senders_with_stats.append((sender, email_count, unread, replied, important))

    senders_with_stats.sort(key=lambda x: x[1], reverse=True)
    for stats in senders_with_stats[0:200]:
        percent_read = 100.0 - (stats[2] * 100.0 / stats[1])
        logging.info(
            f"Sender: {stats[0].name} ({stats[0].email}) {stats[1]} unread: {percent_read}% replied: {stats[3]} important: {stats[4]}"
        )
    return senders_with_stats
