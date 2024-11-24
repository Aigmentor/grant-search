import os


class MODE_ENUM:
    PRODUCTION = "production"
    LOCAL = "local"


# DECRYPT_KEY=os.environ['SECRETS_KEY']


def get_mode():
    return (
        MODE_ENUM.PRODUCTION
        if os.environ.get("HEROKU_LOCAL") is None
        else MODE_ENUM.LOCAL
    )
