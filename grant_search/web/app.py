import logging
import os
from pathlib import Path

from flask import Flask, request, session, redirect, url_for
from werkzeug.exceptions import NotFound

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


if __name__ == "__main__":
    app.run(debug=True)
