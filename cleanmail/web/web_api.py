from functools import wraps
import logging
from flask import Blueprint, jsonify, session


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


@api.route("/scan_email", methods=["POST"])
@login_required
def analyze_email(user, credentials, session):
    queue_scan_email_task(user)
    return jsonify({"status": "success", "email": user.email})


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})
