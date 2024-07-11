from functools import wraps
import logging
from threading import Thread
from flask import Blueprint, jsonify, request, session
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from google.auth.transport.requests import Request

from cleanmail.db.database import get_scoped_session, get_session
import cleanmail.gmail.scan as scan
from cleanmail.gmail.stats import compute_user_status
import cleanmail.web.oauth as oauth
import cleanmail.db.models as db
from cleanmail.worker.dispatcher import queue_scan_email_task, queue_clean_email_task

# XHR API for web app
api = Blueprint("api", __name__)


def get_username():
    return session.get("username")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = oauth.get_credentials_from_flask_session()
        is_logged_in = credentials is not None and not credentials.expired
        if not is_logged_in:
            return jsonify({"error": "Not logged in"}), 400
        session = get_session()
        user = db.GoogleUser.get_or_create(
            session, get_username(), oauth.serialize_credentials(credentials)
        )
        return f(user, credentials, session, *args, **kwargs)

    return decorated_function


@api.route("/auth")
def auth():
    credentials = oauth.get_credentials_from_flask_session()
    is_logged_in = credentials is not None and not credentials.expired
    if is_logged_in:
        try:
            # Attempt to refresh the credentials if possible
            credentials.refresh(Request())

        except Exception as e:
            # Handle the exception (e.g., token is revoked or network issues)
            print(f"Error refreshing credentials: {e}")
            is_logged_in = False

    return jsonify({"isLoggedIn": is_logged_in})


@api.route("/status")
@login_required
def handle_status(user, credentials, session):
    is_logged_in = credentials is not None and not credentials.expired
    if not is_logged_in:
        return jsonify({"error": "Not logged in"}), 400
    logging.info(f"User: {user.email} {user.status}")
    compute_user_status(session, user)
    return jsonify(
        {
            "email": user.email,
            "status": user.status.status,
            "statusData": user.status.data,
            "emailCount": user.status.email_count,
            "deletedEmails": user.status.deleted_emails,
            "toBeDeletedEmails": user.status.to_be_deleted_emails,
        }
    )


@api.route("/sender_batch")
@login_required
def sender_batch(user, credentials, session):
    senders = (
        session.query(db.GmailSender)
        # Load the addresses for each sender- otherwise we'll make a separate query for each sender
        .options(joinedload(db.GmailSender.addresses))
        .filter(db.GmailSender.user_id == user.id)
        .filter(db.GmailSender.emails_sent > 0)
        .filter(db.GmailSender.status == db.SenderStatus.NONE)
        .order_by(desc(db.GmailSender.emails_sent))
        .all()
    )

    senders = sorted(senders, key=lambda sender: sender.value_prop(), reverse=True)
    senders = senders[:5]
    return stats_for_senders(senders, use_threshold=False)


@api.route("/sender_stats")
@login_required
def sender_stats(user, credentials, session):
    senders = (
        session.query(db.GmailSender)
        # Load the addresses for each sender- otherwise we'll make a separate query for each sender
        .options(joinedload(db.GmailSender.addresses))
        .filter(db.GmailSender.user_id == user.id)
        .filter(db.GmailSender.emails_sent > 0)
        .order_by(desc(db.GmailSender.emails_sent))
        .all()
    )
    return stats_for_senders(senders, use_threshold=True)


def stats_for_senders(senders, use_threshold=True):
    totals = [sender.emails_sent for sender in senders]
    total_emails = sum(totals)
    running_sum = []
    current_sum = 0
    threshold_index = None
    # Compute the 80% threshold index- how many senders make up 80% of the emails
    for num in totals:
        current_sum += num
        running_sum.append(current_sum)
        if threshold_index is None and current_sum > total_emails * 0.8:
            threshold_index = len(running_sum)
    if use_threshold:
        senders = senders[:threshold_index]

    if total_emails == 0:
        return jsonify({})

    sender_stats = [
        {
            "addresses": [
                {
                    "name": address.name,
                    "email": address.email,
                    "emailCount": address.email_count,
                    "id": address.id,
                }
                for address in sender.addresses
            ],
            "id": sender.id,
            "name": sender.get_primary_address().name,
            "email": sender.get_primary_address().email,
            "shouldBeCleaned": sender.status == db.SenderStatus.CLEAN,
            "emailsSent": sender.emails_sent,
            "percentOfEmails": sender.emails_sent * 100.0 / total_emails,
            "emailsUnread": sender.emails_unread,
            "emailsImportant": sender.emails_important,
            "emailsReplied": sender.emails_replied,
            "readFraction": sender.read_fraction(),
            "repliedFraction": sender.replied_fraction(),
            "importantFraction": sender.important_fraction(),
            "importanceScore": sender.importance_score(),
            "importantSender": sender.important_fraction() > 0.2
            or sender.replied_fraction() > 0.05,
            "valueProp": sender.value_prop(),
            "personalDomain": sender.is_personal_domain(),
        }
        for sender in senders
    ]
    return jsonify({"senders": sender_stats})


def background_compute_user_status(user_id):
    with get_scoped_session() as session:
        user = session.get(db.GoogleUser, user_id)
        if user is None:
            logging.error(f"User {user_id} not found")
            return
        compute_user_status(session, user)


@api.route("/update_senders", methods=["POST"])
@login_required
def update_senders(user, credentials, session):
    senders = request.json.get("senders")
    action = request.json.get("action")
    logging.info(f"Marking as {action}: {senders}")
    for sender in senders:
        sender = session.get(db.GmailSender, sender)
        if sender is not None:
            sender.status = db.SenderStatus[action.upper()]
    session.commit()
    queue_clean_email_task(user)
    Thread(target=background_compute_user_status, args=[user.id]).start()
    return jsonify({"status": "success"})


@api.route("/scan_email", methods=["POST"])
@login_required
def analyze_email(user, credentials, session):
    queue_scan_email_task(user)
    return jsonify({"status": "success", "email": user.email})


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})


@api.route("/split_address", methods=["POST"])
@login_required
def split_address(user, credentials, session):
    address_id = request.json.get("address_id")
    action = request.json.get("action")
    logging.info(f"{action} address: {address_id}")
    address = session.get(db.GmailSenderAddress, address_id)
    if address is None or address.user_id != user.id:
        return jsonify({"error": "Address not found"}), 400

    address_action = db.SenderStatus.NONE
    if action == "clean":
        address_action = db.SenderStatus.CLEAN
    elif action == "keep":
        address_action = db.SenderStatus.KEEP

    new_address = scan.split_address(session, address, address_action)

    return jsonify(
        {
            "status": "success" if new_address else "failure",
            "newAddress": new_address.id,
        }
    )
