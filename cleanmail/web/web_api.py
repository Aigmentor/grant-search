from functools import wraps
from flask import Blueprint, jsonify, session


from cleanmail.db.database import get_session
import cleanmail.web.oauth as oauth
import cleanmail.db.models as db

# XHR API for web app
api = Blueprint('api', __name__)

def get_username():
    return session.get('username')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = oauth.get_credentials_from_flask_session()
        is_logged_in = credentials is not None and not credentials.expired        
        if not is_logged_in:
            return jsonify({'error': 'Not logged in'}), 400
        session = get_session()
        user = db.GoogleUser.get_or_create(session, get_username())
        return f(user, credentials, session, *args, **kwargs)
    return decorated_function

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
    db_session = get_session()
    user = db.GoogleUser.get_or_create(db_session, get_username(), oauth.serialize_credentials(credentials))       
    return jsonify({'status': user.status.status, 'email': user.email})

@login_required
@api.route("/analyze_email")
def analyze_email(user, credentials, session):    
    return jsonify({'status': 'success', 'email': user.email})

@api.route("/logout", methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'success'})