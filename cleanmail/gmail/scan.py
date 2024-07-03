import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
import random
import re
import sys
import threading
from cleanmail import common
from cleanmail.db.database import get_scoped_session, get_session
from cleanmail.db.models import GmailSender, GmailSenderAddress, GoogleUser, GmailThread
from cleanmail.gmail import api as gmail_api
from cleanmail.gmail.parallel_list import list_thread_ids_by_query_in_parallel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from cleanmail.gmail.clean_user import DELETED_LABEL

# Fewer threads in production. It's closer to DB and so hits gmail api much faster
# with fewer threads
MAX_PROCESS_EMAIL_THREADS = (
    6 if common.get_mode() == common.MODE_ENUM.PRODUCTION else 20
)

sender_lock = threading.Lock()

# Maps from user_id to a dictionary of email_Name to sender.id
sender_cache = defaultdict(dict)


def _find_sender_address(session, user_id: str, email: str, name: str):
    return (
        session.query(GmailSenderAddress)
        .filter(
            GmailSenderAddress.user_id == user_id,
            or_(GmailSenderAddress.email == email, GmailSenderAddress.name == name),
        )
        .all()
    )


def _get_sender_address(
    session, cache: dict, user_id: str, email: str, name: str
) -> GmailSenderAddress:
    cache_key = f"{user_id}_{email}"
    sender_address = cache.get(cache_key)
    if sender_address is not None:
        return sender_address
    sender_lock.acquire()
    try:
        sender = None
        # First try to find in DB by email or name
        sender_addresses = _find_sender_address(session, user_id, email, name)

        if len(sender_addresses) == 0:
            # Need to create a new Sender- no matches on either name or email
            sender = GmailSender(user_id=user_id)
            session.add(sender)
            session.commit()

        exact_sender_address = None
        for sender_address in sender_addresses:
            if sender_address.email == email and sender_address.name == name:
                exact_sender_address = sender_address
                break

        if exact_sender_address is None:
            if len(sender_addresses) > 0:
                sender = sender_addresses[0].sender
            else:
                # Sender already created
                assert sender is not None

            exact_sender_address = GmailSenderAddress(
                user_id=user_id, name=name, email=email, sender_id=sender.id
            )

            session.add(exact_sender_address)
            session.commit()

        cache[cache_key] = (exact_sender_address.sender_id, exact_sender_address.id)
    finally:
        sender_lock.release()

    return exact_sender_address.sender_id, exact_sender_address.id


_EMAIL_HEADER_PATTERN = r"(?:(?P<name>.+?)\s+)?(?:<(?P<email>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)>)|(?P<email_only>[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+)"


def extract_sender_from_headers(headers):
    from_email = None
    name = None
    for header in headers:
        if header["name"].lower() == "from":
            if from_email is None:
                # Only use the sender on first email in thread
                header_line = header["value"]
                match = re.search(_EMAIL_HEADER_PATTERN, header_line)
                if match:
                    from_email = (
                        match.group("email") or match.group("email_only").lower()
                    )
                    name = match.group("name") or from_email
                    return from_email, name
                else:
                    print(f"Failed to match: {headers}")
    return None, None


def _process_thread_by_id(
    user_google_credentials, sender_cache: dict, user_id: str, thread_id: str
):
    try:
        message = gmail_api.get_thread_by_id(user_google_credentials, thread_id)
        if message is None:
            logging.warn(f"Failed to get message for thread_id: {thread_id}")
            return
        with get_scoped_session() as session:
            labels = set()
            max_date = None
            thread_size = len(message["messages"])
            from_email = None
            name = None
            for message in message["messages"]:
                # Some weird emails don't have any labels
                if "labelIds" in message:
                    for label in message["labelIds"]:
                        labels.add(label)
                headers = message["payload"]["headers"]
                if (from_email is None or name is None) and headers:
                    from_email, name = extract_sender_from_headers(headers)

                date = int(message["internalDate"])
                if max_date is None or date > max_date:
                    max_date = date

            if name is None:
                print(f"Failed to find From header in: {headers}")
                return

            if max_date is not None:
                max_date = datetime.datetime.fromtimestamp(max_date / 1000)

            replied = "SENT" in labels
            is_unread = "UNREAD" in labels
            is_important = "IMPORTANT" in labels
            is_deleted = DELETED_LABEL in labels
            thread = session.query(GmailThread).filter_by(thread_id=thread_id).first()
            if thread is not None:
                pass
            else:
                sender_id, sender_address_id = _get_sender_address(
                    session, sender_cache, user_id, from_email, name
                )
                thread = GmailThread(
                    thread_id=thread_id,
                    user_id=user_id,
                    is_read=not is_unread,
                    sender_id=sender_id,
                    sender_address_id=sender_address_id,
                    has_replied=replied,
                    is_singleton=thread_size == 1,
                    is_important=is_important,
                    deleted=is_deleted,
                    most_recent_date=max_date,
                    labels=",".join(labels),
                )
                session.add(thread)
                session.commit()
            return thread
    except Exception as e:
        logging.exception(f"Error processing thread {thread_id}: {e}")


def scan(
    session: Session, user: GoogleUser, sample: int = 2000, max_items: int = 200000
) -> bool:
    """
    Scans a user's emails and stores them in the database
    Returns True if the scan retrieved all the user's emails, False otherwise
    """
    try:
        user_id = user.id
        status = user.status
        status.status = "scanning"
        session.commit()
        # First check what we've already scanned
        count = session.query(GmailThread).filter_by(user_id=user_id).count()
        logging.info(f"Already scanned {count} emails for user {user.email}")

        user_credentials = user.get_google_credentials()
        start_time = datetime.datetime.now()
        message_ids = list_thread_ids_by_query_in_parallel(user_credentials, "")
        logging.info(
            f"Listed {len(message_ids)} message ids in {datetime.datetime.now() - start_time}s"
        )
        if count >= len(message_ids):
            logging.info("No new emails to scan")
            return True

        user.total_email_count = len(message_ids)
        session.commit()
        existing_thread_query = (
            session.query(GmailThread)
            .filter_by(user_id=user_id)
            .with_entities(GmailThread.thread_id)
        )
        existing_thread_ids = set([x[0] for x in existing_thread_query.all()])
        message_ids = [x for x in message_ids if x["id"] not in existing_thread_ids]
        logging.info(
            f"Sampling {sample} of {len(message_ids)}. Sample rate: {sample * 100.0/len(message_ids)}%"
        )

        scanning_all_remaining = True
        if len(message_ids) > sample:
            message_ids = random.sample(message_ids, sample)
            scanning_all_remaining = False
        sender_cache = dict()

        start_time = datetime.datetime.now()
        with ThreadPoolExecutor(max_workers=MAX_PROCESS_EMAIL_THREADS) as executor:
            results = executor.map(
                lambda msg: _process_thread_by_id(
                    user_credentials, sender_cache, user_id, msg["id"]
                ),
                message_ids,
            )
            for i, result in enumerate(results):
                if i % 500 == 499:
                    time_elapsed = datetime.datetime.now() - start_time
                    logging.info(
                        f"Processed {i+1} messages in {time_elapsed.total_seconds()}s: {(i+1.0)/time_elapsed.total_seconds()} messages/s"
                    )
                    status.data = {
                        "email_count": session.query(GmailThread)
                        .filter(GmailThread.user_id == user_id)
                        .count(),
                    }
                    session.commit()
        status.status = "scanned"

        status.data = {
            "last_scan": datetime.datetime.now().isoformat(),
            "email_count": session.query(GmailThread)
            .filter(GmailThread.user_id == user_id)
            .count(),
        }
    except Exception as e:
        logging.exception(f"Error scanning emails: {e}")
        status.status = "scanning error"
        status.data = {
            "last_scan": datetime.datetime.now().isoformat(),
            "scan_error": str(e),
        }
        return False
    session.commit()
    logging.info(f"Scanning finished for user: {scanning_all_remaining}")
    return scanning_all_remaining


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    parser = argparse.ArgumentParser(description="Prints stats for a user's emails")
    parser.add_argument(
        "--email", type=str, help="Email address of user to scan", required=True
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Emails to Sample. If not set only existing scanned emails are used",
        default=None,
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode run", default=False
    )

    args = parser.parse_args()

    session = get_session()
    user = session.query(GoogleUser).filter_by(email=args.email).first()
    if user is None:
        raise Exception(f"User not found for email: '{args.email}'")

    if args.sample:
        print(f"Sampling {args.sample} emails")
        scan(
            session,
            user,
            args.sample,
            max_items=args.sample * 5 if args.debug else None,
        )
