from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
from time import sleep
from typing import List

from grant_search import common
from grant_search.gmail.api import exec_with_rate_limit, list_thread_ids_by_query

MAX_PROCESS_EMAIL_THREADS = (
    7 if common.get_mode() == common.MODE_ENUM.PRODUCTION else 10
)


def _with_retry(callable, *args, **kwargs):
    try:
        return callable(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error: {e}")
        return callable(*args, **kwargs)


from typing import List


def list_thread_ids_by_query_in_parallel(
    credentials: str,
    query: str,
) -> List[str]:
    """
    Retrieve a list of thread IDs by executing queries in parallel.
    Queries are parallelized by month and returned in a single list.

    Args:
        credentials (str): The credentials for accessing the Gmail API.
        query (str): The query string to filter the emails.

    Returns:
        List[str]: A list of thread IDs matching the query.

    """
    # partition by month
    after_time = None
    futures = []
    with ThreadPoolExecutor(max_workers=MAX_PROCESS_EMAIL_THREADS) as executor:
        for year in range(2003, 2026):
            for month in range(1, 13):
                before_time = f"{year}/{month}/01"
                if after_time is None:
                    after_time = before_time
                    continue

                time_query = f"{query} after:{after_time} before:{before_time}"
                futures.append(
                    (
                        after_time,
                        executor.submit(
                            exec_with_rate_limit,
                            list_thread_ids_by_query,
                            credentials,
                            time_query,
                            10000,
                        ),
                    )
                )
                after_time = before_time
                # Stop querying if we're in the future
                if (
                    datetime.datetime.strptime(after_time, "%Y/%m/%d")
                    > datetime.datetime.now()
                ):
                    break

        results_by_year = defaultdict(list)
        results = []
        for date, future in futures:
            ids = future.result()
            results.extend(ids)
            # year = date[:4]
            # results_by_year[year].append(ids)
            # if len(results_by_year[year]) == 12:
            #     logging.info(f"{year}: {sum(len(x) for x in results_by_year[year])}")

    return results
