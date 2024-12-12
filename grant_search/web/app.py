import logging
import os
from pathlib import Path
from urllib.parse import quote_plus, urlencode

from flask import Flask, request, session, redirect, url_for
from werkzeug.exceptions import NotFound

from authlib.integrations.flask_client import OAuth

from werkzeug.middleware.proxy_fix import ProxyFix

from grant_search.common import MODE_ENUM, get_mode
import grant_search.db.models as db
from grant_search.db.database import get_session
import grant_search.web.web_api as web_api

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


if get_mode() == MODE_ENUM.LOCAL:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__, static_folder="../../static")
app.secret_key = os.environ["FLASK_SECRET_KEY"]

app.register_blueprint(web_api.api, url_prefix="/api")

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

if get_mode() == MODE_ENUM.LOCAL:
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,  # Number of trusted proxies for IP
        x_proto=1,  # Number of trusted proxies for protocol
        x_host=1,  # Number of trusted proxies for host
        x_port=1,  # Number of trusted proxies for port
        x_prefix=1,  # Number of trusted proxies for path prefix
    )

db.init_db()


@app.route("/")
def index():
    logging.info(f"Index page from: {app.static_folder}")
    return app.send_static_file("index.html")


@app.route("/grants")
def grants():
    logging.info(f"Index page from: {app.static_folder}")
    return app.send_static_file("grants.html")


@app.route("/datasource")
def datasource():
    logging.info(f"Index page from: {app.static_folder}")
    return app.send_static_file("datasource.html")


@app.errorhandler(NotFound)
def handle_static_missing(e):
    path = Path(request.path)
    if path.suffix == "" and request.path.startswith("/static"):
        new_path = request.path[8:] + ".html"
        return app.send_static_file(new_path)
    else:
        return "File not found.", 404


@app.route("/auth/login")
def login():
    logging.info(f"Calback url: {url_for("callback", _external=True)}")
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/auth/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    # Extract user info from token
    userinfo = token.get("userinfo", {})
    user_email = userinfo.get("email")
    username = userinfo.get("nickname") or userinfo.get("name")

    # Store in session
    session["user_email"] = user_email
    session["username"] = username
    return redirect("/")


@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + os.getenv("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": os.getenv("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


if __name__ == "__main__":
    app.run(debug=True)
