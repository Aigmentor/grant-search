import logging
import os

from flask import Flask, request, session, redirect, url_for
from cleanmail.common import MODE_ENUM, get_mode
import cleanmail.db.models as db
import cleanmail.web.oauth as oauth
import cleanmail.web.web_api as web_api
logging.basicConfig(level=logging.DEBUG)

if get_mode() == MODE_ENUM.LOCAL:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__, static_folder='../static')
app.secret_key = os.environ['FLASK_SECRET_KEY']

app.register_blueprint(web_api.api, url_prefix='/api')

db.init_db()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route("/app/login/<string:state>")
def login(state: str):
    logging.info(f"Login with state {state} on {request.user_agent}")
    return oauth.start_oauth_flow(state)


@app.route("/app/oauth_redirect")
def handle_login():
    if oauth.oauth_handle_redirect():
        credentials = oauth.get_credentials_from_flask_session()
        status = 'login_success'
        user = db.GoogleUser.get_or_create_user(session.get('username'), oauth.serialize_credentials(credentials))       
    else:
        status = 'login_failure'

    return redirect(url_for('index', status=status))


if __name__ == '__main__':
    app.run(debug=True)