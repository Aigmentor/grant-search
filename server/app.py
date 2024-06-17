import logging
import os
from flask import Flask, jsonify, request, session, redirect, url_for
from server.common import MODE_ENUM, get_mode
import server.oauth as oauth
if get_mode() == MODE_ENUM.LOCAL:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__, static_folder='../static')
app.secret_key = os.environ['FLASK_SECRET_KEY']
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route("/api/auth")
def auth():
    credentials = oauth.get_credentials_from_flask_session()
    is_logged_in = credentials is not None and not credentials.expired
    return jsonify({'isLoggedIn': is_logged_in})

@app.route("/app/login/<string:state>")
def login(state: str):
    logging.info(f"Login with state {state} on {request.user_agent}")
    return oauth.start_oauth_flow(state)


@app.route("/app/oauth_redirect")
def handle_login():
    if oauth.oauth_handle_redirect():
        credentials = oauth.get_credentials_from_flask_session()
        status = 'login_success'
    else:
        status = 'login_failure'

    return redirect(url_for('index', status=status))


if __name__ == '__main__':
    app.run(debug=True)