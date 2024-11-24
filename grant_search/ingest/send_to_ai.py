import os
from typing import List, Optional
from instructor import Instructor, from_openai
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import logging
from pydantic import BaseModel, Field
import traceback

from grant_search.ai.common import format_for_llm, ai_client
from grant_search.db.database import Session
from grant_search.db.models import Grant, GrantDerivedData

logger = logging.getLogger(__name__)


class GrantAnalysis(BaseModel):
    dei: bool = Field(
        description="""
        Set to true if the title/description mention things related to DEI, such as
        PoCs, Women, gay or trans. 
        """,
    )
    primary_dei: bool = Field(
        description="""
        Set to true if the title/description related to research primarily related to DEI,
        such as PoCs, Women, LGTBQ, Inequality or other DEI-related topics.
        """,
    )
    hard_science: bool = Field(
        description="""
        Set to true if the title/description related to research primarily related to Hard Scientific
        research, such as Chemistry, Physics, Medicine, Biology, Geology, Space, etc..
        """,
    )
    carbon: bool = Field(
        description="""
        Set to true if the title/description related to research primarily related 
        Global Warming or CO2 emissions and impacts.
        """,
    )


MODEL = "gpt-4o"

SYSTEM_PROMPT = """
Process the grant description below to answer the questions in the model.
"""
MAX_WORKERS = 4


class SendToAI:
    client: Instructor

    def __init__(self):
        self.client = ai_client

    def process_single_grant(self, grant: Grant) -> GrantAnalysis:
        try:
            if isinstance(grant.raw_text, bytes):
                text = grant.raw_text.decode("utf-8")
            else:
                text = grant.raw_text
            messages = format_for_llm(SYSTEM_PROMPT, text)
            logger.info(f"Processing grant: {grant.id}")
            results = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_model=GrantAnalysis,
                max_tokens=1024,
            )
            return (grant, results)
        except Exception as e:
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            logger.error(f"Error processing grant {grant.id}: {str(e)}")

    def process_grants(self, grants: List[Grant]):

        # Use ThreadPoolExecutor to process grants in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all grants for processing
            futures = [
                executor.submit(self.process_single_grant, grant) for grant in grants
            ]

            # Wait for all futures to complete
            with Session() as session:
                for future in futures:
                    try:
                        result = future.result()
                        if result:
                            grant, analysis = result
                            derived_data = GrantDerivedData(
                                grant_id=grant.id,
                                dei=analysis.dei,
                                primary_dei=analysis.primary_dei,
                                hard_science=analysis.hard_science,
                                political_science=None,
                                carbon=analysis.carbon,
                            )
                            session.add(derived_data)
                            logger.info(f"Saved derived data for grant {grant.id}")
                    except Exception as e:
                        logger.error(f"Stack trace:\n{traceback.format_exc()}")
                        logger.error(f"Thread execution failed: {str(e)}")
                session.commit()
