import logging
import os
from flask import Flask, request, session, redirect, url_for
from grant_search.db.database import get_session
from grant_search.common import MODE_ENUM, get_mode
import grant_search.db.models as db
import grant_search.web.web_api as web_api

logging.basicConfig(level=logging.DEBUG)

if get_mode() == MODE_ENUM.LOCAL:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__, static_folder="../static")
app.secret_key = os.environ["FLASK_SECRET_KEY"]

app.register_blueprint(web_api.api, url_prefix="/api")

db.init_db()


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True)
