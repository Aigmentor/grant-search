import csv
from datetime import datetime
import gzip
import json
import os
import tempfile
import urllib.request
import zipfile
from urllib.parse import urlparse
import io
import logging
import xml.etree.ElementTree as ET
import ssl

from grant_search.db.models import Agency, DataSource, Grant, Grantee
from grant_search.db.database import Session
from grant_search.ingest.nih import API_URL, get_nih_grants_by_year
from grant_search.ingest.send_to_ai import SendToAI


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def xml_string_to_dict(xml_string: str):
    tree = ET.fromstring(xml_string)
    return _xml_to_dict(tree)


def _xml_to_dict(element):
    result = {}
    # Add element attributes if any exist
    if element.attrib:
        result.update(element.attrib)

    # Handle child elements
    for child in element:
        child_dict = _xml_to_dict(child)
        child_tag = child.tag

        if child_tag in result:
            # If key exists, convert to list if not already
            if not isinstance(result[child_tag], list):
                result[child_tag] = [result[child_tag]]
            result[child_tag].append(child_dict)
        else:
            result[child_tag] = child_dict

    # Handle element text
    if element.text and element.text.strip():
        if result:  # If we have child elements/attributes
            result["text"] = element.text.strip()
        else:
            result = element.text.strip()

    return result


class Ingester:
    source: str
    agency: str
    source_name: str

    def __init__(self, source_name: str, source: str, agency: str):
        self.source = source
        self.agency = agency
        self.source_name = source_name

        if self.agency != "NIH":
            assert self.source, "Source (--input_url) is required for non-NIH data"
        else:
            self.source = f"{API_URL}?year={self.source_name}"

        if self.agency not in ["NIH", "NSF"]:
            raise Exception("Agency must be in [NIH, NSF]")

    def _get_content(self) -> tuple[io.BytesIO, str]:
        # Check if source is URL or local file
        parsed = urlparse(self.source)
        is_url = bool(parsed.scheme)
        print(f"Getting {self.source} {is_url}")
        # Get file object either from URL or local path
        if is_url:
            logger.info(f"Downloading: {self.source}")
            # Create an SSL context that ignores certificate verification
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(self.source, context=context)
            file_content = response.read()

            # Try to get filename from Content-Disposition header
            filename = None
            if "Content-Disposition" in response.headers:
                cd = response.headers["Content-Disposition"]
                if "filename=" in cd:
                    filename = cd.split("filename=")[1].strip('"')

            # Fall back to URL path if no Content-Disposition
            if not filename:
                filename = os.path.basename(parsed.path)

            # If still no filename, use a default
            if not filename:
                filename = "downloaded_file"

            logger.info(f"Detected filename: {filename}")
        else:
            with open(self.source, "rb") as f:
                file_content = f.read()
            filename = os.path.basename(self.source)

        return io.BytesIO(file_content), filename

    def _handle_zip(self, filename, file_content: io.BytesIO):
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()

        # Extract zip contents to temp directory
        with zipfile.ZipFile(file_content, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        i = 0
        # Walk through all files in temp directory
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                i += 1
                file_path = os.path.join(root, file)
                with open(file_path, "rt") as f:
                    self.process_file(file_path, f.read())

    def process_file(self, file_name, content):
        if file_name.endswith(".xml"):
            data = xml_string_to_dict(content)
            # For NSF data:
            award = data["Award"]
            award_id = award["AwardID"]
            title = award["AwardTitle"]
            start_date = datetime.strptime(award["AwardEffectiveDate"], "%m/%d/%Y")
            end_date = datetime.strptime(award["AwardExpirationDate"], "%m/%d/%Y")
            amount = award["AwardAmount"]
            description = award["AbstractNarration"]
            if description is None or len(description) == 0:
                description = "No description provided"
            investigators = award["Investigator"]
            if type(investigators) != list:
                investigators = [investigators]
            investigators = [x["PI_FULL_NAME"] for x in investigators]
            # Create grantees from investigators
            grantees = []
            for investigator in investigators:
                # Check if grantee already exists
                grantee = (
                    self.session.query(Grantee)
                    .filter(Grantee.name == investigator)
                    .first()
                )
                if not grantee:
                    logger.info(f"Creating new grantee: {investigator}")
                    grantee = Grantee(name=investigator)
                    self.session.add(grantee)
                grantees.append(grantee)
            self.session.commit()
            grant = Grant(
                title=title,
                start_date=start_date,
                end_date=end_date,
                amount=float(amount),
                description=description,
                award_id=award_id,
                data_source_id=self.data_source.id,
                raw_text=content.encode(),
            )
            # Add grantees to grant
            grant.grantees.extend(grantees)
            self.session.add(grant)
            self.session.commit()
            logger.info(f"Created grant: {title}")

    def process_nih(self):
        year = self.source_name.split(" ")[1]
        logger.info(f"Processing NIH grants for {year}")
        for data in get_nih_grants_by_year(year):
            try:
                award_id = data["appl_id"]
                title = data["project_title"]
                amount = data["award_amount"] or 0.0
                description = data["abstract_text"]
                investigators = data["principal_investigators"]
                if type(investigators) != list:
                    investigators = [investigators]
                investigators = [
                    x["first_name"] + " " + x["last_name"] for x in investigators
                ]
                # Parse dates from NIH format
                start_date = datetime.strptime(
                    data["project_start_date"], "%Y-%m-%dT%H:%M:%SZ"
                )
                end_date = datetime.strptime(
                    data["project_end_date"], "%Y-%m-%dT%H:%M:%SZ"
                )

                # Create grantees from investigators
                grantees = []
                for investigator in investigators:
                    # Check if grantee already exists
                    grantee = (
                        self.session.query(Grantee)
                        .filter(Grantee.name == investigator)
                        .first()
                    )
                    if not grantee:
                        logger.info(f"Creating new grantee: {investigator}")
                        grantee = Grantee(name=investigator)
                        self.session.add(grantee)
                    grantees.append(grantee)
                self.session.commit()

                grant = Grant(
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    amount=float(amount),
                    description=description,
                    award_id=award_id,
                    data_source_id=self.data_source.id,
                    raw_text=json.dumps(data).encode(),
                )
                # Add grantees to grant
                grant.grantees.extend(grantees)
                self.session.add(grant)
                self.session.commit()
                logger.info(f"Created grant: {title}")
            except Exception as e:
                logger.error(
                    f"Error creating grant: {e} in {json.dumps(data, indent=2)}"
                )

    def ingest(self):
        self.session = Session()
        session = self.session
        # Check for existing agency
        agency = session.query(Agency).filter(Agency.name == self.agency).first()
        if not agency:
            logger.warn(f"Creating agency: {self.agency}")
            agency = Agency(name=self.agency)
            session.add(agency)
            session.commit()
            session.refresh(agency)

        print(f"agency: {agency.id}")
        self.data_source = session.query(DataSource).filter(
            DataSource.name == self.source_name and DataSource.agency_id == agency.id
        ).first() or (
            self.source
            and session.query(DataSource)
            .filter(
                DataSource.origin == self.source and DataSource.agency_id == agency.id
            )
            .first()
        )
        if self.data_source:
            logger.info(f"Found existing data source: {self.source}")
            # Delete existing grants for this data source
            grants_to_delete = (
                session.query(Grant)
                .filter(Grant.data_source_id == self.data_source.id)
                .all()
            )
            for grant in grants_to_delete:
                session.delete(grant)
            session.commit()
            logger.info(
                f"Deleted {len(grants_to_delete)} existing grants for data source: {self.source}"
            )
        else:
            logger.warn(f"Creating source: {self.source}")
            self.data_source = DataSource(
                name=self.source_name,
                timestamp=datetime.now(),
                agency_id=agency.id,
                origin=self.source,
            )
            session.add(self.data_source)
            session.commit()
            logger.info(f"Created data source: {self.source}")

        if self.agency == "NIH":
            self.process_nih()
        else:
            file_content, filename = self._get_content()

            # Handle compressed files
            if filename.endswith(".zip"):
                self._handle_zip(filename, file_content)

            elif filename.endswith(".gz"):
                file_content = io.BytesIO(gzip.decompress(file_content))
                # Remove .gz
                new_filename = self.source[0:-3]
                self.process_file(new_filename, file_content)

            self.process_file(filename, file_content)

        # Process grants through AI after ingestion

        logger.info("Processing grants through AI...")
        with Session() as session:
            grants = (
                session.query(Grant)
                .filter(Grant.data_source_id == self.data_source.id)
                .all()
            )

            if grants:
                ai_processor = SendToAI()
                ai_processor.process_grants(grants)
                logger.info(f"Processed {len(grants)} grants through AI")
            else:
                logger.warn("No grants found to process through AI")
