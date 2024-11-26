import os
from typing import List, Optional
from instructor import Instructor, from_openai
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import logging
from pydantic import BaseModel, Field
import traceback

from sqlalchemy.orm import undefer

from grant_search.ai.common import format_for_llm, ai_client
from grant_search.db.database import Session
from grant_search.db.models import DEIStatus, Grant, GrantDerivedData

logger = logging.getLogger(__name__)


class GrantAnalysis(BaseModel):
    dei_status: DEIStatus = Field(
        description="""
        none - No mention of DEI
        mentions_dei - The grant mentions DEI, but is not focused on DEI, perhaps just using the word "diversity"
        partial_dei - The grant isn't focused on DEI, but DEI concepts are important in the design or research.
        primarily_dei - The grant is focused on DEI and the research strongly concerns DEI concepts or topics.
        """,
    )
    dei_women: bool = Field(
        description="""
        Set to true if the grant mentions women or gender in the title or description.
        """,
    )

    dei_race: bool = Field(
        description="""
        Set to true if the grant mentions race or ethnicity in the title or description.
        """,
    )

    outrageous: bool = Field(
        description="""
        Set to true if the grant is outrageous involving DEI or other non-science topics directly
        into research on real topics, such as "Indigenous Science" or "Indigenous Knowledge".
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

    def complete_partial_grants(self):
        with Session() as session:
            query = (
                session.query(Grant)
                .options(undefer(Grant.raw_text))
                .filter(Grant.derived_data == None)
                .all()
            )
            logger.info(f"Processing {len(query)} partial grants")
            self.process_grants(query)

    def complete_all_grants(self):
        with Session() as session:
            query = session.query(Grant).all()
            logger.info(f"Processing {len(query)} grants")
            self.process_grants(query)

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
            session = Session()
            for i, future in enumerate(futures):
                try:
                    result = future.result()
                    if result:
                        grant, analysis = result
                        # Delete existing derived data if present
                        existing = (
                            session.query(GrantDerivedData)
                            .filter(GrantDerivedData.grant_id == grant.id)
                            .first()
                        )
                        if existing:
                            session.delete(existing)
                            session.flush()

                        derived_data = GrantDerivedData(
                            grant_id=grant.id,
                            **analysis.model_dump(),
                        )
                        session.add(derived_data)
                        logger.info(f"Saved derived data for grant {grant.id}")
                        if i % 20 == 0:
                            session.commit()
                            session = Session()
                except Exception as e:
                    logger.error(f"Stack trace:\n{traceback.format_exc()}")
                    logger.error(f"Thread execution failed: {str(e)}")
                session.commit()
