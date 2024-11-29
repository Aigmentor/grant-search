from datetime import datetime, timedelta
import json
import time
from typing import Generator
import logging
import requests

logger = logging.getLogger(__name__)
API_URL = "https://api.reporter.nih.gov/v2/projects/search"

INTERVAL_DAYS = 14


def _get_nih_grants_from(
    start_date: datetime, end_date: datetime
) -> Generator[dict, None, None]:
    request = {
        "criteria": {
            "project_start_date": {
                "from_date": start_date.strftime("%Y-%m-%d"),
                "to_date": end_date.strftime("%Y-%m-%d"),
            },
        },
        "limit": 500,
    }
    start_index = 0
    search_id = None
    while True:
        request["offset"] = start_index
        response = requests.post(API_URL, json=request)
        time.sleep(1)
        content = response.json()
        for grant in content["results"]:
            # logger.info(f"NIH grant: {grant['project_title']} {grant['appl_id']}")
            # print(json.dumps(grant, indent=2))
            yield grant

        if search_id is None:
            search_id = content["meta"]["search_id"]
            request["searchId"] = search_id

        start_index += len(content["results"])
        # print(f"meta: {content['meta']}")
        if start_index >= content["meta"]["total"]:
            print(f"Reached total count {content['meta']['total']}")
            break


def get_nih_grants_by_year(year: str) -> Generator[dict, None, None]:
    start_date = datetime(int(year), 1, 1)
    end_date = datetime(int(year), 12, 31)
    while start_date < end_date:
        next_date = start_date + timedelta(days=INTERVAL_DAYS)

        for grant in _get_nih_grants_from(start_date, min(next_date, end_date)):
            yield grant
        start_date = next_date


if __name__ == "__main__":
    total = 0
    for grant in get_nih_grants_by_year("2024"):
        if total == 0:
            print(json.dumps(grant, indent=2))
        total += 1
    print(total)
