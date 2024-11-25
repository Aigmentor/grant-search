from datetime import datetime
import logging
from concurrent.futures import Future
from threading import Thread
from typing import Dict, List, Optional, Tuple

from grant_search.ai.filter_string_to_function import query_by_text
from grant_search.db.database import get_session
from grant_search.db.models import Grant, GrantSearchQuery

logger = logging.getLogger(__name__)


class QueryThread:
    id: int

    def __init__(self, query: str):
        global query_thread_id
        self.query = query
        self.id = query_thread_id
        self.results = None

        query_thread_id += 1
        Thread(target=self.run_query, daemon=True).start()

    def is_done(self):
        return self.results is not None

    def run_query(self):
        with get_session() as session:
            self.results = query_by_text(session, self.query)


def _run_query(query_id: int):
    with get_session() as session:
        grant_search_query = session.query(GrantSearchQuery).get(query_id)
        results = query_by_text(session, grant_search_query)
        grant_search_query.grants = [result for result, _ in results]
        grant_search_query.reasons = [reason for _, reason in results]
        grant_search_query.complete = True
        session.commit()


def create_query(query: str) -> int:
    """Creates a new grant search query in the database and starts processing it asynchronously.

    Args:
        query (str): The natural language query string to search grants with

    Returns:
        int: The ID of the created GrantSearchQuery record

    The query is processed in a background thread. The results can be retrieved by checking
    the GrantSearchQuery record's complete flag and accessing its grants and reasons fields.
    """
    with get_session() as session:
        grant_search_query = GrantSearchQuery(
            complete=False, query=query, timestamp=datetime.now()
        )
        session.add(grant_search_query)
        session.commit()
        Thread(target=_run_query, daemon=True, args=[grant_search_query.id]).start()
        return grant_search_query.id
