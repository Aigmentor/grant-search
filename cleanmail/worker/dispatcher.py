import argparse
from concurrent.futures import ThreadPoolExecutor
import time
import json
import logging
from typing import Optional

from cleanmail import common
from cleanmail.gmail.stats import compute_stats
from cleanmail.gmail.clean_user import clean_email_for_user

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
import sys
import threading

from cleanmail.gmail import scan
from cleanmail.db.redis import publish, subscribe
from cleanmail.db.models import GmailSender, GoogleUser
from cleanmail.db import database

_MAX_SCAN_THREADS = 5
_WORKER_TASKS_QUEUE = "worker_queue"
_MESSAGE_TYPE = "worker_task"


class _TASK_ENUM:
    SCAN_EMAIL: str = "scan_email"
    CLEAN_EMAIL: str = "clean_email"


def queue_scan_email_task(user: GoogleUser):
    _send_background_task(_TASK_ENUM.SCAN_EMAIL, {"user_id": user.id})


def queue_clean_email_task(user: GoogleUser):
    _send_background_task(_TASK_ENUM.CLEAN_EMAIL, {"user_id": user.id})


def _send_background_task(task_name: str, spec: dict):
    queue_spec = {"task_name": task_name, **spec}
    publish(_WORKER_TASKS_QUEUE, queue_spec, _MESSAGE_TYPE)
    logging.info(f"Sent {task_name} to queue")


def _process_scan_email(user_id: int):
    session = database.get_scoped_session()
    user = session.get(GoogleUser, user_id)
    if user is None:
        logging.error(f"User {user_id} not found")
        return

    logging.info(f"Processing scan email for user {user.email}")
    scan.scan(session, user, 10000)
    compute_stats(session, user)
    logging.info(f"Finished processing scan email for user {user.email}")


def _process_clean_email(user_id: int):
    clean_email_for_user(user_id)


def _process_queue_entry(queue_spec):
    logging.info(f"Worker got task: {json.dumps(queue_spec)}")

    task_name = queue_spec.get("task_name")
    if task_name == _TASK_ENUM.SCAN_EMAIL:
        user_id = queue_spec.get("user_id")
        _process_scan_email(user_id)
    elif task_name == _TASK_ENUM.CLEAN_EMAIL:
        user_id = queue_spec.get("user_id")
        _process_clean_email(user_id)


def _consume_queue():
    pubsub = subscribe(_WORKER_TASKS_QUEUE)
    for pubsub_message in pubsub.listen():
        try:
            if pubsub_message["type"] == "message":
                msg_dict = json.loads(pubsub_message["data"])
                thread = threading.Thread(
                    target=_process_queue_entry, args=[msg_dict["data"]]
                )
                thread.start()
        except Exception as e:
            logging.exception(f"Error consuming queue: {e}")


def scan_user(user_id: int) -> Optional[GoogleUser]:
    session = database.get_scoped_session()
    user = session.get(GoogleUser, user_id)
    logging.info(f"Scanning user {user.email}")
    is_complete = scan.scan(
        session,
        user,
        10000 if common.get_mode() == common.MODE_ENUM.PRODUCTION else 500,
    )
    compute_stats(database.get_scoped_session(), session.get(GoogleUser, user_id))
    return None if is_complete else user_id


def scan_users():
    logging.info("Scanning all users")
    session = database.get_session()
    users = session.query(GoogleUser).all()
    logging.info(f"Found {len(users)} users to scan")
    user_ids = [user.id for user in users]
    with ThreadPoolExecutor(max_workers=_MAX_SCAN_THREADS) as executor:
        while len(user_ids) > 0:
            results = executor.map(scan_user, user_ids)
            user_ids = [user_id for user_id in results if user_id is not None]
            logging.info(f"Remaining users to scan: {len(user_ids)}")


def reset_clean_status():
    logging.info("Resetting clean status")
    session = database.get_session()
    users = session.query(GoogleUser).all()
    for user in users:
        user.status.is_cleaning = False
    session.commit()


if __name__ == "__main__":
    logging.info("Starting worker")
    parser = argparse.ArgumentParser(
        description="Queue worker for Processing background tasks"
    )
    args = parser.parse_args()
    threading.Thread(target=scan_users).start()
    reset_clean_status()
    _consume_queue()
