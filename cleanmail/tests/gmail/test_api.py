import datetime
import unittest
from unittest.mock import patch

import cleanmail.db.database as database
from cleanmail.db.models import GoogleUser
from cleanmail.gmail.api import (
    get_service,
    list_thread_ids_by_query,
)

class GmailAPITestCase(unittest.TestCase):
    @patch("cleanmail.gmail.api.build")
    def test_get_service(self, mock_build):
        credentials = "dummy_credentials"
        service = get_service(credentials)
        mock_build.assert_called_once_with("gmail", "v1", credentials=credentials, cache_discovery=True)
        self.assertIsNotNone(service)

    def test_list_thread_ids_by_query(self):
        session = database.get_session()
        user = session.query(GoogleUser).filter_by(email="josh.sacks@gmail.com").first()
        self.assertIsNotNone(user)
        message_ids = list_thread_ids_by_query(user.get_google_credentials(), "", 400)        
        self.assertIsNotNone(message_ids)
        self.assertEqual(len(message_ids), 400)

        # Now check "after: 2 days from now" which should return no results
        after_time = datetime.datetime.now() + datetime.timedelta(days=2)
        message_ids = list_thread_ids_by_query(user.get_google_credentials(), f"after: {after_time.strftime('%Y/%m/%d')}", 20)        
        self.assertIsNotNone(message_ids)
        self.assertEqual(len(message_ids), 0)
        
    

    # Add more tests here...

if __name__ == "__main__":
    unittest.main()