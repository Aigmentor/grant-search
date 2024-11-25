from concurrent.futures import ThreadPoolExecutor
import os
import random
import traceback
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from sqlalchemy.orm import undefer

from grant_search.ai.common import ai_client, format_for_llm
from grant_search.db.models import (
    Agency,
    DataSource,
    Grant,
    GrantDerivedData,
    GrantSearchQuery,
)

# logging.getLogger("instructor").setLevel(logging.DEBUG)

TOP_LEVEL_MODEL = "gpt-4o"
FILTER_MODEL = "gpt-4o-mini"

logger = logging.getLogger(__name__)


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

    has_dei: Optional[bool] = Field(
        description="If True then filter for grants which mention DEI in the description"
    )

    has_dei_focus: Optional[bool] = Field(
        description="If True then filter for grants which strongly focus on DEI as part of the research program."
    )


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
        description="Reason for the answer. This parameter must be first"
    )
    result: bool = Field(description="True/False answer to the question")


SYSTEM_PROMPT = """
You are an expert at filtering grants based on the grant description.
You will be given a description of the grants you want to find, 
Fill out the results with appropriate JSON as described by the schema.
If the query involves DEI topics like Women's studies then it probably is looking
for grants with a DEI focus.
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
) -> List[Grant]:
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

    if lsf.has_dei is not None or lsf.has_dei_focus is not None:
        query = query.join(GrantDerivedData, GrantDerivedData.grant_id == Grant.id)

        if lsf.has_dei is not None:
            query = query.filter(GrantDerivedData.dei == True)
        if lsf.has_dei_focus is not None:
            query = query.filter(GrantDerivedData.primary_dei == True)

    return query.all()


def filter_grants_by_query(user_query: str, grant: Grant) -> Tuple[bool, str]:
    prompt = f"""
    You are answering this question: `{user_query}`
    You will be given a grant description. Use that to answer this question with
    True/False in the `results` field.
    The response must be in JSON format.
    """
    try:
        messages = format_for_llm(prompt, f'grant_description: \n"{grant.raw_text}"')
        result = ai_client.chat.completions.create(
            model=FILTER_MODEL,
            messages=messages,
            response_model=GrantFilter,
        )
        return result.result, result.reason
    except Exception as e:
        logger.error(f"Error filtering grant {grant.id}: {e}")
        return False, "Error"


def query_by_text(session, query: GrantSearchQuery) -> List[Tuple[Grant, str]]:
    search_function = _get_search_function(query.query)
    grants = _filter_grants_from_linear(session=session, lsf=search_function)

    if len(grants) > 500:
        logger.info(f"Sampling down from {len(grants)} to 500 grants")
        sampling_fraction = 500.0 / len(grants)
        grants = random.sample(grants, k=int(len(grants) * sampling_fraction))
    else:
        sampling_fraction = 1.0

    query.sampling_fraction = sampling_fraction
    session.commit()
    filtered_grants = []
    with ThreadPoolExecutor(max_workers=200) as executor:
        # Create list of futures for each grant query
        logging.info(f"{len(grants)} grants to scan")
        futures = [
            executor.submit(
                filter_grants_by_query, search_function.grant_question, grant
            )
            for grant in grants
        ]
        # Process results as they complete
        for i, (grant, future) in enumerate(zip(grants, futures)):
            try:
                included, reason = future.result()
                if included:
                    # reference grant.data_source.gency totrigger a load
                    grant.data_source.agency
                    filtered_grants.append((grant, reason))

                if i % 100 == 99:
                    logging.info(f"Processed {i+1} grants")
            except Exception as e:
                logger.error(f"Stack trace:\n{traceback.format_exc()}")
                logger.error(f"Error processing grant {grant.id}: {e}")

    logger.info(f"Filtered down to {len(filtered_grants)} grants")
    return filtered_grants
