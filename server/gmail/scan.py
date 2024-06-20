import datetime
import logging
import random
from cleanemail.db.models import GoogleEmail, GoogleUser
from gmail import api as gmail_api

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
    email_ids = gmail_api.list_messages_by_query(user.credentials, 'after:' + oldest_email_date.strftime('%Y/%m/%d'), max * 10)
    if email_ids > max:
        email_ids = random.sample(email_ids, max)

    for email_id in email_ids:
        email = gmail_api.get_message(user.credentials, email_id)
        if email:
            gmail_email = GoogleEmail(gmail_id=email_id, user_id=user.id, date_sent=email['date'])
            gmail_email.save()
            logging.info(f"Saved email {email_id} for user {user.email}")
        else:
            logging.error(f"Failed to fetch email {email_id} for user {user.email}")
