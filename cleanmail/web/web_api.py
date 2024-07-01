from functools import wraps
import logging
from flask import Blueprint, jsonify, session
from sqlalchemy import desc


from cleanmail.db.database import get_session
import cleanmail.web.oauth as oauth
import cleanmail.db.models as db
from cleanmail.worker.dispatcher import queue_scan_email_task

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
    return jsonify({"isLoggedIn": is_logged_in})


@api.route("/status")
@login_required
def handle_status(user, credentials, session):
    is_logged_in = credentials is not None and not credentials.expired
    if not is_logged_in:
        return jsonify({"error": "Not logged in"}), 400
    logging.info(f"User: {user.email} {user.status}")
    return jsonify(
        {
            "status": user.status.status,
            "statusData": user.status.data,
            "email": user.email,
        }
    )


@api.route("/sender_stats")
@login_required
def sender_stats(user, credentials, session):
    print("here1")
    senders = (
        session.query(db.GmailSender)
        .filter(db.GmailSender.user_id == user.id)
        .filter(db.GmailSender.emails_sent > 0)
        .order_by(desc(db.GmailSender.emails_sent))
        .all()
    )
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

    senders = senders[:threshold_index]

    if total_emails == 0:
        return jsonify({})
    sender_stats = [
        {
            "name": sender.name,
            "email": sender.email,
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
        }
        for sender in senders
    ]
    return jsonify({"senders": sender_stats})


@api.route("/scan_email", methods=["POST"])
@login_required
def analyze_email(user, credentials, session):
    queue_scan_email_task(user)
    return jsonify({"status": "success", "email": user.email})


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})
