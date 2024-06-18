from flask import Blueprint, jsonify, session


import server.oauth as oauth
import server.db.models as db

# XHR API for web app
api = Blueprint('api', __name__)

@api.route("/auth")
def auth():
    credentials = oauth.get_credentials_from_flask_session()
    is_logged_in = credentials is not None and not credentials.expired
    return jsonify({'isLoggedIn': is_logged_in})

@api.route("/status")
def handle_status():
    credentials = oauth.get_credentials_from_flask_session()
    is_logged_in = credentials is not None and not credentials.expired
    if not is_logged_in:
        return jsonify({'error': 'Not logged in'}), 400
    user = db.GoogleUser.get_or_create(session.get('username'), oauth.serialize_credentials(credentials))       
    return jsonify({'status': user.status.status, 'email': user.email})
