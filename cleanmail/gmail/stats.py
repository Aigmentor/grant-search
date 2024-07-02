from sqlalchemy import or_
from sqlalchemy.orm import Session

from cleanmail.db.models import GmailSender, GmailThread, GoogleUser


def compute_user_status(session: Session, user: GoogleUser):
    status_json = user.status.data
    deleted_count = (
        session.query(GmailThread)
        .filter(GmailThread.user_id == user.id, GmailThread.deleted == True)
        .count()
    )
    status_json["deleted_emails"] = deleted_count
    all_email_count = (
        session.query(GmailThread).filter(GmailThread.user_id == user.id).count()
    )
    status_json["email_count"] = all_email_count
    status_json["deleted_percent"] = float(
        f"{deleted_count * 100.0 / all_email_count:.3g}"
    )
    session.commit()


def compute_stats(session: Session, user: GoogleUser):
    senders = session.query(GmailSender).filter_by(user_id=user.id).all()
    for sender in senders:
        threads = (
            session.query(GmailThread)
            .filter(
                GmailThread.user_id == user.id,
                GmailThread.sender == sender.id,
                or_(GmailThread.deleted.is_(None), GmailThread.deleted == False),
            )
            .all()
        )
        email_count = len(threads)
        # Senders can have 0 threads if all their emails were deleted
        if email_count == 0:
            # session.delete(sender)
            continue
        replied = 0
        unread = 0
        important = 0
        deleted = 0
        for thread in threads:
            if thread.has_replied:
                replied += 1
            if not thread.is_read:
                unread += 1
            if "IMPORTANT" in thread.labels:
                important += 1
            if thread.deleted:
                deleted += 1

        sender.emails_sent = email_count
        sender.emails_important = important
        sender.emails_replied = replied
        sender.emails_unread = unread
        sender.emails_deleted = deleted
        session.commit()
