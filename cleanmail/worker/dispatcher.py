import argparse
import json
import logging
import sys
import threading

from db.redis import publish, subscribe
from cleanmail.db.models import GoogleUser

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

_WORKER_TASKS_QUEUE = 'worker_queue'
_MESSAGE_TYPE = "worker_task"
class _TASK_ENUM:
    SCAN_EMAIL: str = 'scan_email'

def queue_scan_email_task(user: GoogleUser):
    _send_background_task(_TASK_ENUM.SCAN_EMAIL, {'user_id': user.id})


def _send_background_task(task_name: str, spec: dict):
    queue_spec = {
        'task_name': task_name,
        **spec
    }
    publish(_WORKER_TASKS_QUEUE, queue_spec, _MESSAGE_TYPE)
    logging.info(f"Sent {task_name} to queue")


def _process_scan_email(user_id: int):
    user = GoogleUser.get_by_id(user_id)
    if user is None:
        logging.error(f"User {user_id} not found")
        return

    logging.info(f"Processing scan email for user {user.email}")
    
    # Do some processing here
    logging.info(f"Finished processing scan email for user {user.email}")

def _process_queue_entry(queue_spec):
    task_name = queue_spec.get('task_name')
    if task_name == _TASK_ENUM.SCAN_EMAIL:
        user_id = queue_spec.get('user_id')
        _process_scan_email(user_id)

def _consume_queue():
    pubsub = subscribe(_WORKER_TASKS_QUEUE)
    for pubsub_message in pubsub.listen():
        try:
            if pubsub_message['type'] == 'message':
                msg_dict = json.loads(pubsub_message['data'])
                thread = threading.Thread(target=_process_queue_entry, args=[msg_dict['data']])
                thread.start()
        except Exception as e:
            logging.exception(f'Error consuming queue: {e}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Queue worker for Processing background tasks')
    args = parser.parse_args()

    _consume_queue()