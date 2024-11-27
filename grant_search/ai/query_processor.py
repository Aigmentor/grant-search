from datetime import datetime
import logging
from threading import Thread

from grant_search.ai.filter_string_to_function import query_by_text
from grant_search.db.database import get_session
from grant_search.db.models import Grant, GrantSearchQuery

logger = logging.getLogger(__name__)


def _run_query(query_id: int):
    try:
        with get_session() as session:
            grant_search_query = session.query(GrantSearchQuery).get(query_id)
            results = query_by_text(session, grant_search_query)
            grants = []
            reasons = []
            for i, (result, reason) in enumerate(results):
                result = session.query(Grant).get(result.id)
                grants.append(result)
                reasons.append(reason)
                grant_search_query.grants = grants
                grant_search_query.reasons = reasons
                if i % 100 == 99 or i == 5:
                    session.add(grant_search_query)
                    logging.info(f"Processed {i+1} grants")
                    session.commit()
                    session.begin()
                    session.refresh(grant_search_query)

            logging.info(f"Done processing {len(grants)} grants in query_processor")
            grant_search_query.complete = True
            session.commit()
    except Exception as e:
        import traceback

        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        logger.error(f"Error processing query {query_id}: {e}")


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
        # Check for existing completed query with same text
        existing_query = (
            session.query(GrantSearchQuery)
            .filter(
                GrantSearchQuery.query_text == query, GrantSearchQuery.complete == True
            )
            .first()
        )

        if existing_query:
            logger.info(f"Found existing completed query with text: {query}")
            return existing_query.id

        grant_search_query = GrantSearchQuery(
            complete=False, query=query, timestamp=datetime.now(), query_text=query
        )
        session.add(grant_search_query)
        session.commit()
        Thread(target=_run_query, daemon=True, args=[grant_search_query.id]).start()
        return grant_search_query.id
