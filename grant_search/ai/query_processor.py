from concurrent.futures import Future
from threading import Thread
from typing import Dict, List, Optional, Tuple

from grant_search.ai.filter_string_to_function import query_by_text
from grant_search.db.database import get_session
from grant_search.db.models import Grant

query_thread_id = 0


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


class QueryProcessor:
    in_flight_queries: Dict[int, QueryThread]

    def __init__(self):
        self.in_flight_queries = {}

    def process_query(self, query: str) -> int:
        query_thread = QueryThread(query)
        self.in_flight_queries[query_thread.id] = query_thread
        return query_thread.id

    def get_results(self, query_id: int) -> Optional[List[Tuple[Grant, str]]]:
        if query_id not in self.in_flight_queries:
            return []
        results = self.in_flight_queries.get(query_id).results
        if results:
            del self.in_flight_queries[query_id]
        return results
