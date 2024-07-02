import datetime
from email.mime.text import MIMEText
from time import sleep
from typing import Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import email
import logging

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


class CustomFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("Refreshing credentials")


logger = logging.getLogger("google_auth_httplib2")
logger.addFilter(CustomFilter())
import threading
import random
from concurrent.futures import ThreadPoolExecutor
from googleapiclient.errors import HttpError

MAX_THREADS = 3

rate_limit_date = datetime.datetime.now()


def exec_with_rate_limit(func: callable, *args, **kwargs):
    global rate_limit_date
    for i in range(5):
        try:
            if datetime.datetime.now() < rate_limit_date:
                sleep_time = (
                    rate_limit_date
                    - datetime.datetime.now()
                    + datetime.timedelta(seconds=random.random())
                ).total_seconds()
                sleep(sleep_time)
            return func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status == 403 and i < 4:
                delay = (i + 3) * 10
                logging.info("Rate limit hit, waiting %s seconds", delay)
                rate_limit_date = datetime.datetime.now() + datetime.timedelta(
                    seconds=delay
                )
                continue
            if e.resp.status == 400:
                logging.info("Bad request for: %s", args)
                return None
            else:
                raise e


def page_all_items(func: callable, item_key: str, max_items: int = None) -> list:
    """
    Retrieves all items from a paginated API endpoint.

    Args:
        func (callable): The function to call for retrieving the next page of items.
          callable should be a lambda which takes the `next_page_token` to set in the call
        item_key (str): The key to access the list of items in the results dictionary.
        max_items (int, optional): The maximum number of items to retrieve. Defaults to None.

    Returns:
        list: A list of all retrieved items.
    """
    items = []
    next_page_token = None
    # Rest of the function implementation goes here
    while max_items is None or len(items) < max_items:
        try:
            results = func(next_page_token)
        except HttpError as e:
            logging.info("Error: %s", e)
            results = func(next_page_token)

        items.extend(results.get(item_key, []))
        next_page_token = results.get("nextPageToken")
        if next_page_token is None:
            break

    if max_items:
        return items[0:max_items]
    else:
        return items


def get_service(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials, cache_discovery=True)


def get_message_by_id(credentials, message_id: str) -> dict:
    return _get_message_by_id(get_service(credentials), message_id)


def _get_message_by_id(service, message_id: str) -> dict:
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )
        msg_str = base64.urlsafe_b64decode(msg["raw"])
        msg_str = msg_str.decode("utf-8")
        mime_msg = email.message_from_string(msg_str, policy=email.policy.default)
        mime_msg.add_header("RIO-Message-ID", message_id)
        mime_msg.add_header("RIO-Thread-ID", msg["threadId"])

        return mime_msg
    except Exception as e:
        logging.info("Error: %s", e)
        return None


thread_local = threading.local()


def get_local_service(credentials: Credentials):
    if not hasattr(thread_local, "service"):
        thread_local.service = get_service(credentials)
    return thread_local.service


def get_message_by_id_on_thread(credentials, message_id: str) -> dict:
    get_local_service(credentials)
    msg = (
        thread_local.service.users()
        .messages()
        .get(userId="me", id=message_id, ormat="metadata")
        .execute()
    )
    # mime_msg = _get_message_by_id(thread_local.service, message_id)
    # msg_bytes = base64.urlsafe_b64decode(msg['raw'])
    print("msg", msg)
    return (message_id, msg) if msg is not None else None


def _get_latest_message_by_gthread_id(service, gthread_id: str) -> Optional[dict]:
    try:
        gthread_data = (
            service.users().threads().get(userId="me", id=gthread_id).execute()
        )

        # get the ID of the latest message in the thread
        latest_msg_id = gthread_data["messages"][-1]["id"]
        # print("thread data", gthread_data)
        # logging.info(f"Retrieved gthread {gthread_id} data with {len(gthread_data['messages'])} messages, latest_msg_id {latest_msg_id}")
        # msg = thread_local.service.users().messages().get(userId='me', id=message_id, ormat='metadata').execute()

        return gthread_id, _get_message_by_id(service, latest_msg_id)
    except Exception as e:
        logging.info("Error: %s", e)
        return None


# get (gthread_id, latest EmailMessage on the specified Gmail thread), otherwise None
def get_latest_message_by_gthread_id_on_thread(
    credentials, gthread_id: str
) -> Optional[Tuple[str, dict]]:
    # logging.info(f"Getting latest message on thread {gthread_id}")
    get_local_service(credentials)
    return (
        thread_local.service.users().threads().get(userId="me", id=gthread_id).execute()
    )


def watch_for_new_emails(credentials: Credentials, stop: bool = False):
    service = get_service(credentials)
    if stop:
        response = service.users().stop(userId="me").execute()
    else:
        request = {
            "labelIds": ["INBOX"],
            "topicName": "projects/project-rio-413018/topics/new_gmail",
        }
        response = service.users().watch(userId="me", body=request).execute()
    logging.info("Watch response for (stop=%s): %s", stop, response)
    return response


def list_messages_by_message_id(credentials, messages: list, max_items: int) -> dict:
    resolved_messages = {}
    if not messages:
        return {}
    else:
        messages = messages[0:max_items]
        by_id = {}
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            results = executor.map(
                lambda msg: get_message_by_id_on_thread(credentials, msg),
                [x["id"] for x in messages],
            )
        results = [r for r in results if r is not None]
        by_id = dict(results)
        # Now add them to the hash in the order of the original list
        for message in messages:
            if message["id"] in by_id:
                resolved_messages[message["id"]] = by_id[message["id"]]
            else:
                logging.info("Could not resolve message: %s", message["id"])
        return resolved_messages


def get_thread_by_id(credentials, thread_id: str) -> dict:
    return exec_with_rate_limit(
        get_latest_message_by_gthread_id_on_thread, credentials, thread_id
    )


# list messages by message ID from a list of threads, using the latest message in each thread
def list_messages_by_gthread_id(
    credentials: Credentials, gthreads: list, max_items: int
) -> dict:
    resolved_messages = {}
    if not gthreads:
        logging.info("No gmail threads found.")
        return resolved_messages
    else:
        gthreads = gthreads[0:max_items]
        by_id = {}
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            results = executor.map(
                lambda gthread_id: get_thread_by_id(credentials, gthread_id),
                [x["id"] for x in gthreads],
            )
        results = [r for r in results if r is not None]
        return results


def list_message_ids_by_query(
    credentials: Credentials, query: str, max: int = 30
) -> list[str]:
    service = get_local_service(credentials=credentials)
    return page_all_items(
        lambda next_page_token: service.users()
        .messages()
        .list(pageToken=next_page_token, userId="me", q=query)
        .execute(),
        "messages",
        max,
    )


def list_messages_by_query(credentials: Credentials, query: str, max: int = 30) -> dict:
    messages = list_message_ids_by_query(credentials, query, max)
    return list_messages_by_message_id(credentials, messages, max)


def list_messages_since_history_id(
    credentials: Credentials, start_history_id: str
) -> Tuple[str, dict, list]:
    service = get_service(credentials=credentials)

    changes = page_all_items(
        lambda next_page_token: service.users()
        .history()
        .list(
            userId="me",
            startHistoryId=start_history_id,
            labelId="INBOX",
            pageToken=next_page_token,
        )
        .execute(),
        "history",
        None,
    )
    # logging.info("History results: %s", json.dumps(changes, indent=2))
    # changes = results.get('history', [])
    messages = []
    removed_messages = []
    latest_history_id = start_history_id
    for element in changes:
        id = element["id"]
        if id > latest_history_id:
            latest_history_id = id
        new_emails = element.get("messagesAdded", [])
        for email in new_emails:
            message_id = email["message"]["id"]
            labels = email["message"]["labelIds"]
            if "SENT" in labels:
                logging.info("Skipping sent email: %s", message_id)
            else:
                messages.append(email["message"])
        deleted_emails = element.get("messagesDeleted", [])

        for email in deleted_emails:
            removed_messages.append(email["message"]["id"])

        modified_emails = element.get("labelsRemoved", [])
        for email in modified_emails:
            labels = email["labelIds"]
            if "INBOX" in labels:
                removed_messages.append(email["message"]["id"])

    logging.info(
        f"Found {len(messages)} new emails and {len(removed_messages)} removed emails from {start_history_id} to {latest_history_id}"
    )
    return (
        latest_history_id,
        list_messages_by_message_id(credentials, messages, len(messages)),
        removed_messages,
    )


# function to list messages ids from gmail matching a query string, organized by thread
# gets latest threads and returns a mapping of gthread ID to the latest message in the thread
def list_thread_ids_by_query(
    credentials: Credentials,
    query: str,
    max: int = 30,
) -> dict:
    service = get_local_service(credentials=credentials)

    return page_all_items(
        lambda next_page_token: service.users()
        .threads()
        .list(pageToken=next_page_token, userId="me", q=query, maxResults=500)
        .execute(),
        "threads",
        max,
    )


# function to list messages from gmail matching a query string, organized by thread
# gets latest threads and returns a mapping of gthread ID to the latest message in the thread
def list_thread_messages_by_query(
    credentials: Credentials, query: str, max: int = 30
) -> dict:
    service = get_service(credentials=credentials)

    gthreads = page_all_items(
        lambda next_page_token: service.users()
        .threads()
        .list(pageToken=next_page_token, userId="me", q=query)
        .execute(),
        "threads",
        max,
    )

    return list_messages_by_gthread_id(credentials, gthreads, max)


def _create_raw_message(sender, to, subject, message_text, gthread_id=None):
    message = MIMEText(message_text)
    message["to"] = ",".join(to)
    message["from"] = sender
    message["subject"] = subject

    # this did not work for Gmail threading, instead adding the thread_id below
    # message['References'] = gthread_id

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message, "thread_id": gthread_id}


def draft_reply(credentials: Credentials, user_id: str, gthread_id: str, body: str):
    logging.log(logging.INFO, f"Creating draft reply for gtread_id {gthread_id}")
    try:
        _, original_msg = get_latest_message_by_gthread_id_on_thread(
            credentials, gthread_id
        )
    except Exception as e:
        raise Exception(f"Unknown gthread_id: {gthread_id}")
    to = original_msg["from"]
    subject = original_msg["subject"]

    # Create a MIMEText message
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    # Encode the message in base64url format
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    raw_draft = {"message": {"raw": raw_message, "threadId": gthread_id}}

    try:
        service = get_service(credentials=credentials)
        draft = service.users().drafts().create(userId="me", body=raw_draft).execute()
        draft_id = draft["id"]
        message_id = draft["message"]["id"]
        print(f"Draft ID: {draft_id}\nDraft message: {draft['message']}")
        return f"https://mail.google.com/mail/#inbox?compose={message_id}"
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def create_draft(
    credentials: Credentials, user_id: str, to_list: list[str], subject: str, body: str
) -> str:
    logging.log(logging.INFO, f"Creating draft for {to_list} with subject {subject}")
    raw_message = _create_raw_message(user_id, to_list, subject, body)
    draft = {"message": raw_message}
    try:
        service = get_service(credentials=credentials)
        draft = service.users().drafts().create(userId=user_id, body=draft).execute()
        draft_id = draft["id"]
        message_id = draft["message"]["id"]
        print(f"Draft ID: {draft_id}\nDraft message: {draft['message']}")
        return f"https://mail.google.com/mail/#inbox?compose={message_id}"
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def _create_label(service, label_name: str):
    logging.info(f"Creating label {label_name}")
    label = {"name": label_name}
    response = service.users().labels().create(userId="me", body=label).execute()
    return response["id"]


def get_or_create_label_id(service, label_name) -> str:
    labels_response = service.users().labels().list(userId="me").execute()
    labels = labels_response.get("labels", [])

    # Find the label ID for 'rio_archive'
    label_id = None
    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    return _create_label(service, label_name)


def add_label(service, thread_id: str, label_id: str):
    commands = {"addLabelIds": [label_id], "removeLabelIds": []}
    response = (
        service.users()
        .threads()
        .modify(userId="me", id=thread_id, body=commands)
        .execute()
    )
    return True


# TODO: There is an issue where if the Gmail thread has multiple messages, this only remove the inbox label
# from the latest message, so the thread stays in the inbox.
# def archive_email(credentials: Credentials, user_id: str, email_id: str) -> bool:
#     service = get_service(credentials=credentials)
#     label_id = get_or_create_label_id(service, RIO_ARCHIVE_LABEL)
#     commands = {"removeLabelIds": ["INBOX"], "addLabelIds": [label_id]}
#     try:
#         response = (
#             service.users()
#             .messages()
#             .modify(userId=user_id, id=email_id, body=commands)
#             .execute()
#         )
#         logging.info(f"Email {email_id} archived.")
#         return True
#     except HttpError as e:
#         logging.error(f"Error archiving email: {e}")
#         return False


def datetime_from_message(message: dict) -> datetime:
    return datetime.datetime.strptime(message["Date"], "%a, %d %b %Y %H:%M:%S %z")
