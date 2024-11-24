import logging
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from grant_search.db.models import GoogleUser
from grant_search.gmail import api as gmail_api
from grant_search.gmail.scan import compute_sender_stats, scan
import grant_search.db.database as database

logging.basicConfig(level=logging.INFO)


class TestScan(unittest.TestCase):
    def setUp(self):
        self.user = GoogleUser(id=1, email="josh.sacks@gmail.com")
        self.max_items = 1000

    # @patch("server.gmail.scan.GoogleEmail.query")
    # @patch("server.gmail.scan.logging")
    # @patch("server.gmail.scan.gmail_api.list_message_ids_by_query")
    # def test_scan_with_existing_emails(self, mock_list_message_ids, mock_logging, mock_query):
    #     mock_query.filter_by.return_value.count.return_value = 500
    #     oldest_email_date = datetime(2022, 1, 1)
    #     mock_query.filter_by.return_value.order_by.return_value.first.return_value = GoogleEmail(date_sent=oldest_email_date)
    #     messages = ["message1", "message2", "message3"]
    #     mock_list_message_ids.return_value = messages

    #     result = scan(self.user, self.max_items)

    #     mock_query.filter_by.assert_called_once_with(user_id=self.user.id)
    #     mock_query.filter_by.return_value.count.assert_called_once()
    #     mock_query.filter_by.return_value.order_by.assert_called_once_with(GoogleEmail.date_sent)
    #     mock_query.filter_by.return_value.order_by.return_value.first.assert_called_once()
    #     mock_logging.info.assert_called_with(f"Already scanned 500 emails for user {self.user.email}")
    #     mock_list_message_ids.assert_called_once_with(self.user.credentials, f"after:{oldest_email_date.strftime('%Y/%m/%d')}", self.max_items * 10)
    #     self.assertEqual(result, messages)

    def test_scan_basic(self):
        session = database.get_session()
        user = session.query(GoogleUser).filter_by(email="josh.sacks@gmail.com").first()
        self.assertIsNotNone(user)
        messages = scan(session, user, 2000)
        self.assertEqual(len(messages), 2000)

    # @patch("server.gmail.scan.GoogleEmail.query")
    # @patch("server.gmail.scan.logging")
    # @patch("server.gmail.scan.gmail_api.list_message_ids_by_query")
    # @patch("server.gmail.scan.gmail_api.list_messages_by_ids")
    # def test_scan_with_no_existing_emails(self, mock_list_messages_by_ids, mock_list_message_ids, mock_logging, mock_query):
    #     mock_query.filter_by.return_value.count.return_value = 0
    #     oldest_email_date = datetime.now()
    #     mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
    #     messages = ["message1", "message2", "message3"]
    #     mock_list_message_ids.return_value = messages
    #     mock_list_messages_by_ids.return_value = messages

    #     result = scan(self.user, self.max_items)

    #     mock_query.filter_by.assert_called_once_with(user_id=self.user.id)
    #     mock_query.filter_by.return_value.count.assert_called_once()
    #     mock_query.filter_by.return_value.order_by.assert_called_once_with(GoogleEmail.date_sent)
    #     mock_query.filter_by.return_value.order_by.return_value.first.assert_called_once()
    #     mock_logging.info.assert_called_with(f"Already scanned 0 emails for user {self.user.email}")
    #     mock_list_message_ids.assert_called_once_with(self.user.credentials, f"after:{oldest_email_date.strftime('%Y/%m/%d')}", self.max_items * 10)
    #     mock_list_messages_by_ids.assert_called_once_with(self.user.credentials, messages, max_items=self.max_items)
    #     self.assertEqual(result, messages)

    def test_compute_sender_stats(self):
        session = database.get_session()
        user = session.query(GoogleUser).filter_by(email="josh.sacks@gmail.com").first()
        self.assertIsNotNone(user)
        messages = scan(session, user, 20000)
        stats = compute_sender_stats(session, user)


if __name__ == "__main__":
    unittest.main()
