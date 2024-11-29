import argparse
import os
from dotenv import load_dotenv


if __name__ == "__main__":

    load_dotenv()

    # Load after setting up API key
    from grant_search.ingest.ingest import Ingester

    parser = argparse.ArgumentParser(description="Ingest grant data from a URL or file")
    parser.add_argument("--input_url", help="URL or path to input file")
    parser.add_argument("--source_name", help="short name for source", required=True)
    parser.add_argument("--agency", help="Agency name", required=True)

    args = parser.parse_args()

    ingester = Ingester(args.source_name, args.input_url, args.agency)
    ingester.ingest()
