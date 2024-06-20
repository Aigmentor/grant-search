import datetime
import logging
from cleanmail.db.models import GoogleEmail, GoogleUser
from server.gmail import api as gmail_api

def scan(user: GoogleUser, max_items: int = 1000):
    # First check what we've already scanned
    count = GoogleEmail.query.filter_by(user_id=user.id).count()
    logging.info(f"Already scanned {count} emails for user {user.email}")

    oldest_email = GoogleEmail.query.filter_by(user_id=user.id).order_by(GoogleEmail.date_sent).first()
    if oldest_email:
        oldest_email_date = oldest_email.date_sent
    else:
        oldest_email_date = datetime.datetime.now()
    logging.info(f"Oldest email: {oldest_email_date}")

    max = max_items - count
    if (max <= 0):
        logging.info(f"Already scanned {count} emails for user {user.email}")
        return
    
    # Scan 10x as many emails, then subsample.
    gmail_api.list_messages_by_query(user.credentials, 'after:' + oldest_email_date.strftime('%Y/%m/%d'), max * 10)

