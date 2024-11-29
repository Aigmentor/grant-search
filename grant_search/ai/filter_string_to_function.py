from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import threading
from typing import Generator, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from sqlalchemy.orm import undefer
from sqlalchemy.orm.query import Query

from grant_search.ai.common import ai_client, format_for_llm
from grant_search.db.database import get_session
from grant_search.db.models import (
    Agency,
    DEIStatus,
    DataSource,
    Grant,
    GrantDerivedData,
    GrantSearchQuery,
)
from grant_search.ingest.ingest import xml_string_to_dict

# logging.getLogger("instructor").setLevel(logging.DEBUG)

TOP_LEVEL_MODEL = "gpt-4o"
FILTER_MODEL = "gpt-4o-mini"

logger = logging.getLogger(__name__)

GRANT_LIMIT = 1200


class LinearSearchFunction(BaseModel):
    start_date_after: Optional[datetime] = Field(
        description="Start date for the grant must be after this date"
    )
    start_date_before: Optional[datetime] = Field(
        description="Start date for the grant must be before this date"
    )

    # end_date: Optional[datetime] = Field(description="End date for the grant")

    agency: Optional[str] = Field(
        description="Agency name to filter by. Agency name must be exact."
    )

    data_source: Optional[str] = Field(
        description="Data source name to filter by. Data source name is a `like` and can contain '%' for wildcards."
    )

    dei_status: Optional[List[DEIStatus]] = Field(
        description="""
        Filter for grants based on the DEI status. Add all statuses that might apply for the requested search filter:
        none - No mention of DEI
        mentions_dei - The grant mentions DEI, but is not focused on DEI, perhaps just using the word "diversity"
        partial_dei - The grant isn't focused on DEI, but DEI concepts are important in the design or research.
        primarily_dei - The grant is focused on DEI and the research strongly concerns DEI concepts or topics.
        """,
    )

    dei_women: Optional[bool] = Field(
        description="Filter for (True) or out (False) which mention women for DEI purposes."
    )

    dei_race: Optional[bool] = Field(
        description="Filter for (True) or out (False) grants which mention race or ethnicity for DEI purposes."
    )

    outrageous: Optional[bool] = Field(
        description="Filter for (True) or out (False) grants which are outrageous involving DEI or other non-science topics directly"
    )

    hard_science: Optional[bool] = Field(
        description="Filter for (True) or out (False) for grants which are primarily hard science."
    )

    carbon: Optional[bool] = Field(
        description="Filter for (True) or out (False)for grants which are primarily about CO2/global warming."
    )

    amount_min: Optional[float] = Field(description="Minimum amount for the grant")

    amount_max: Optional[float] = Field(description="Maximum amount for the grant")


class SearchFunction(LinearSearchFunction):
    grant_question: Optional[str] = Field(
        description="""
        Optional description text to filter by. This is a question with a true/false answer that can be answered by looking at the grant description.
        """,
        examples=[
            "Does this grant fund organ donation?"
            "Is this grant about DEI?"
            "Are the investigators for this grant from University of Chicago?"
        ],
    )


class GrantFilter(BaseModel):
    reason: str = Field(
        description="Reason for the answer. This parameter must be first. Should be a short sentence or two, no more than 50 tokens"
    )
    result: bool = Field(
        description="True/False answer to the question. Only respond True if the grant clearly and unambiguously matches the question."
    )


SYSTEM_PROMPT = """
You are an expert at filtering grants based on the grant description.
You will be given a description of the grants you want to find, 
Fill out the results with appropriate JSON as described by the schema.
"""


def _get_search_function(text: str) -> SearchFunction:
    text = f"User description: {text}"
    messages = format_for_llm(SYSTEM_PROMPT, text)
    return ai_client.chat.completions.create(
        model=TOP_LEVEL_MODEL,
        messages=messages,
        response_model=SearchFunction,
    )


def _filter_grants_from_linear(
    session,
    lsf: LinearSearchFunction,
) -> Query:
    """
    Filter grants query by LinearSearchFunction

    Returns:
        A SQLAlchemy query that can be used to get the set of grants that match
        the filter criteria.
    """
    logger.info(f"Filtering grants with {lsf}")
    query = session.query(Grant).options(undefer(Grant.raw_text))
    if lsf.data_source:
        datasource_query = session.query(DataSource).filter(
            DataSource.name.like(lsf.data_source)
        )
        datasources = [x.id for x in datasource_query.all()]
        if len(datasources) > 0:
            query = query.filter(Grant.data_source_id in datasources)
        else:
            datasources = None

    if lsf.agency:
        agency_query = session.query(Agency).filter(Agency.name.ilike(lsf.agency))
        agency_result = agency_query.first()
        if agency_result:
            agency_id = agency_result.id
            query = query.join(DataSource, Grant.data_source_id == DataSource.id)
            query = query.filter(DataSource.agency_id == agency_id)

    if lsf.start_date_before:
        query = query.filter(Grant.start_date <= lsf.start_date_before)

    if lsf.start_date_before:
        query = query.filter(Grant.start_date >= lsf.start_date_after)

    if lsf.amount_min:
        query = query.filter(Grant.amount >= lsf.amount_min)

    if lsf.amount_max:
        query = query.filter(Grant.amount <= lsf.amount_max)

    if (
        lsf.dei_status is not None
        or lsf.dei_women is not None
        or lsf.dei_race is not None
        or lsf.outrageous is not None
        or lsf.hard_science is not None
        or lsf.carbon is not None
    ):
        query = query.join(GrantDerivedData, GrantDerivedData.grant_id == Grant.id)
        if lsf.dei_status is not None and len(lsf.dei_status) > 0:
            query = query.filter(GrantDerivedData.dei_status.in_(lsf.dei_status))
        if lsf.dei_women is not None:
            query = query.filter(GrantDerivedData.dei_women == lsf.dei_women)
        if lsf.dei_race is not None:
            query = query.filter(GrantDerivedData.dei_race == lsf.dei_race)
        if lsf.outrageous is not None:
            query = query.filter(GrantDerivedData.outrageous == lsf.outrageous)
        if lsf.hard_science is not None:
            query = query.filter(GrantDerivedData.hard_science == lsf.hard_science)
        if lsf.carbon is not None:
            query = query.filter(GrantDerivedData.carbon == lsf.carbon)

    query = query.order_by(Grant.amount.desc())

    return query


def filter_grants_by_query(user_query: str, grant: Grant) -> Tuple[Grant, bool, str]:
    prompt = f"""
    You are answering this question: `{user_query}`
    You will be given a grant description. Use that to answer this question with
    True/False in the `results` field.
    The response must be in JSON format.
    """
    try:
        if grant.data_source.agency == "NSF":
            grant_json = xml_string_to_dict(grant.raw_text)
            award = grant_json["Award"]
            grant_data = {
                "AwardID": award["AwardID"],
                "AwardTitle": award["AwardTitle"],
                "AwardAmount": award["AwardAmount"],
                "AbstractNarration": award["AbstractNarration"],
                "Investigator": award["Investigator"],
            }
            grant_text = json.dumps(grant_data)
        else:
            grant_text = grant.raw_text

        messages = format_for_llm(prompt, f'grant_description: \n"{grant_text}"')
        result = ai_client.chat.completions.create(
            model=FILTER_MODEL,
            messages=messages,
            response_model=GrantFilter,
            timeout=20,  # 20 second timeout
        )
        return grant, result.result, result.reason
    except Exception as e:
        logger.error(f"Error filtering grant {e}: {grant_text}")
        return grant, False, "Error"


def query_by_text(
    session, query: GrantSearchQuery
) -> Generator[Tuple[Grant, str], None, None]:
    writing_session = get_session()
    query.status = "parsing_query"
    session.commit()
    session.refresh(query)
    search_function = _get_search_function(query.query)
    query.status = "reading_grants"
    session.commit()
    session.refresh(query)
    query_session = get_session()
    sql_query = _filter_grants_from_linear(session=query_session, lsf=search_function)
    grants_count = sql_query.count()
    grants = sql_query.limit(GRANT_LIMIT).all()

    if grants_count > GRANT_LIMIT:
        logger.info(f"Sampling down from {grants_count} to {GRANT_LIMIT} grants")
        sampling_fraction = GRANT_LIMIT / grants_count
    else:
        sampling_fraction = 1.0

    query.sampling_fraction = sampling_fraction
    query.status = "sending_to_ai"
    session.commit()
    session.refresh(query)

    with ThreadPoolExecutor(max_workers=612) as executor:
        # Create list of futures for each grant query
        logging.info(f"{len(grants)} grants to scan")
        futures = [
            executor.submit(
                filter_grants_by_query, search_function.grant_question, grant
            )
            for grant in grants
        ]
        query.status = "waiting_for_ai"
        session.commit()
        session.begin()
        session.refresh(query)
        logging.info(f"Submitted {len(grants)} for analysis")
        # Process results as they complete
        for i, future in enumerate(futures):
            try:
                grant = None
                grant, included, reason = future.result(timeout=12)
                if included:
                    grant.data_source.agency
                    yield (grant, reason)

                if i % 40 == 39:
                    logger.info(f"Processed {i + 1} grants")
            except Exception as e:
                cancelled = future.cancel()
                logger.info(f"Cancelled: {cancelled}")
                # logger.error(f"Stack trace:\n{traceback.format_exc()}")
                logger.error(
                    f"Error processing grant {grant.id if grant else 'unknown'}: {e}"
                )
        logger.info("Done processing all grants1")
        executor.shutdown(wait=False, cancel_futures=True)

    logger.info("Done processing all grants2")
    threads = threading.enumerate()
    for thread in threads:
        logger.info(f"Thread: {thread.name}")
