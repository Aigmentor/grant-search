from concurrent.futures import ThreadPoolExecutor
import os
import traceback
from typing import Optional
from instructor import from_openai
from openai import OpenAI
from pydantic import BaseModel, Field
from datetime import datetime
import logging
from grant_search.ai.common import ai_client, format_for_llm
from grant_search.filter_grants import filter_grants_from_ai

TOP_LEVEL_MODEL = "gpt-4o"
FILTER_MODEL = "gpt-4o-mini"

logger = logging.getLogger(__name__)


class SearchFunction(BaseModel):
    start_date: Optional[datetime] = Field(description="Start date for the grant")

    end_date: Optional[datetime] = Field(description="End date for the grant")

    agency: Optional[str] = Field(
        description="Agency name to filter by. Agency name must be exact."
    )

    data_source: Optional[str] = Field(
        description="Data source name to filter by. Data source name is a `like` and can contain '%' for wildcards."
    )

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
Fill out the results with appropriate JSON as described by the schema
"""


def _get_search_function(text: str) -> SearchFunction:
    text = f"User description: {text}"
    messages = format_for_llm(SYSTEM_PROMPT, text)
    logging.info(messages)
    return ai_client.chat.completions.create(
        model=TOP_LEVEL_MODEL,
        messages=messages,
        response_model=SearchFunction,
    )


def filter_grants_by_query(user_query: str, grant_description: str) -> bool:
    logging.error(f"here1:")
    prompt = f"""
    You are answering this question: `{user_query}`
    You will be given a grant description. Use that to answer this question with
    True/False in the `results` field.
    The response must be in JSON format.
    """
    messages = format_for_llm(prompt, f'grant_description: \n"{grant_description}"')
    logging.error(f"here2: {messages}")
    result = ai_client.chat.completions.create(
        model=FILTER_MODEL,
        messages=messages,
        response_model=GrantFilter,
    )
    logging.info(f"Answer: {result}")
    return result.result


def query_by_text(session, text: str):
    search_function = _get_search_function(text)
    grants = filter_grants_from_ai(
        session=session,
        start_date=search_function.start_date,
        end_date=search_function.end_date,
        agency=search_function.agency,
        datasource=search_function.data_source,
    )
    grants = grants
    logger.info(f"Found {len(grants)} grants")

    filtered_grants = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        # Create list of futures for each grant query
        futures = [
            executor.submit(
                filter_grants_by_query, search_function.grant_question, grant.raw_text
            )
            for grant in grants
        ]

        # Process results as they complete
        for grant, future in zip(grants, futures):
            try:
                if future.result():
                    filtered_grants.append(grant)
            except Exception as e:
                logger.error(f"Stack trace:\n{traceback.format_exc()}")
                logger.error(f"Error processing grant {grant.id}: {e}")

    logger.info(f"Filtered down to {len(filtered_grants)} grants")
    return filtered_grants
