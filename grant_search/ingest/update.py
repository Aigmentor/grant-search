from queue import Queue
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging
import traceback

import dotenv
from pydantic import BaseModel, Field

from grant_search.db.database import get_session
from grant_search.db.models import Grant, GrantDerivedData
from grant_search.ai.common import format_for_llm, get_ai_client

MAX_CONCURRENT_GRANTS = 100
MODEL = "gpt-4o"

PROMPT = """
Process the grant description below to generate a succinct summary of the grant's topic.
"""

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class UpdateModel(BaseModel):
    summary: str = Field(
        description="A succinct (80-120 tokens) summary of the grant's topic and what they hope to achieve.",
    )


# Update this function to check if the grant needs to be updated
def needs_update(grant: Grant):
    # return True
    return grant.derived_data.summary is None


# Modify this function to update the grant with the model-derived data
def update_grant(grant: Grant, results: UpdateModel):
    # logging.info(
    #     f"Updating grant {grant.id} \nx{grant.description} \n\n with summary: {results}"
    # )
    grant.derived_data.summary = results.summary


def process_grant(grant_id: int):
    with get_session() as process_session:
        grant = process_session.get(Grant, grant_id)
        if grant:
            messages = format_for_llm(PROMPT, grant.description)
            results = get_ai_client().chat.completions.create(
                model=MODEL,
                messages=messages,
                response_model=UpdateModel,
                max_tokens=300,
            )
            update_grant(grant, results)
            process_session.commit()
        else:
            print(f"Grant {grant_id} not found")
    return grant_id


def process_grant_queue(grant_queue: Queue):
    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_GRANTS)
    futures = []
    completed = 0

    def complete_future(future):
        nonlocal futures
        nonlocal completed
        grant_queue.task_done()
        futures.remove(future)
        try:
            future.result()
        except Exception as e:
            logger.error(f"Future failed with error: {e}")
        completed += 1
        if completed % 100 == 0:
            logger.info(f"Completed {completed} tasks")

    logger.info("Processing grant queue thread started")
    while True:
        try:
            grant_id = grant_queue.get()
            if grant_id is None:
                grant_queue.task_done()
                break

            futures.append(executor.submit(process_grant, grant_id))
            # Check for completed futures
            if len(futures) >= MAX_CONCURRENT_GRANTS:
                for completed_future in as_completed(futures):
                    complete_future(completed_future)

                    if len(futures) < MAX_CONCURRENT_GRANTS - 5:
                        break
        except Exception as e:
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            logging.error(f"Error processing queued grant {grant_id}: {e}")

    for completed_future in as_completed(futures):
        complete_future(completed_future)


def update_all_grants():
    session = get_session()

    grants = (
        session.query(Grant)
        .join(GrantDerivedData, Grant.id == GrantDerivedData.grant_id, isouter=True)
        .filter(GrantDerivedData.summary.is_(None))
        .yield_per(100)
    )
    grant_queue = Queue(maxsize=400)

    # Start worker thread
    worker = Thread(target=process_grant_queue, args=(grant_queue,), daemon=True)
    worker.start()

    for grant in grants:
        try:
            # Add grant to queue if it needs update
            if needs_update(grant):
                try:
                    grant_queue.put(grant.id, block=False)
                except:
                    print(f"Queue full, skipping grant {grant.id}")

        except Exception as e:
            print(f"Error processing grant {grant.id}: {e}")
            session.rollback()
            continue
    grant_queue.put(None)
    grant_queue.join()


if __name__ == "__main__":
    dotenv.load_dotenv()
    update_all_grants()
