import argparse
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":

    load_dotenv()

    # Load after setting up API key
    from grant_search.ingest.send_to_ai import SendToAI

    parser = argparse.ArgumentParser(description="Refresh derived data")
    parser.add_argument(
        "--partial", action="store_true", help="Only refresh partial data"
    )

    args = parser.parse_args()

    send_to_ai = SendToAI()
    if args.partial:
        send_to_ai.complete_partial_grants()
    else:
        send_to_ai.process_all_grants()
