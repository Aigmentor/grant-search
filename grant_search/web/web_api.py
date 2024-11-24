from functools import wraps
import logging
from threading import Thread
import traceback
from flask import Blueprint, jsonify, request, session
from sqlalchemy import desc

from grant_search.db.models import Grant, Agency, DataSource
from grant_search.db.database import get_session
from grant_search.ai.filter_string_to_function import query_by_text
from grant_search.filter_grants import filter_grants_query

# XHR API for web app
api = Blueprint("api", __name__)


@api.route("/datasources", methods=["GET"])
def get_datasources():
    """Get all data sources"""
    try:
        session = get_session()
        datasources = session.query(DataSource).all()

        return jsonify(
            [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "agency_id": ds.agency_id,
                    "agency_name": ds.agency.name,
                }
                for ds in datasources
            ]
        )

    except Exception as e:
        logging.error(f"Error getting datasources: {str(e)}")
        return jsonify({"error": "Failed to get datasources"}), 500


@api.route("/agencies", methods=["GET"])
def get_agencies():
    """Get all agencies"""
    try:
        session = get_session()

        agencies = session.query(Agency).all()

        return jsonify([{"id": agency.id, "name": agency.name} for agency in agencies])

    except Exception as e:
        logging.error(f"Error getting agencies: {str(e)}")
        return jsonify({"error": "Failed to get agencies"}), 500


@api.route("/grants_by_text", methods=["POST"])
def get_grants_by_text():
    """Get grants filtered by natural language text description"""
    try:
        # Get text from request body
        request_data = request.get_json()
        if not request_data or "text" not in request_data:
            return jsonify({"error": "Missing text parameter"}), 400

        text = request_data["text"]
        with get_session() as session:
            # Query grants using the text filter
            grants = query_by_text(session, text)

            # Format response
            results = [
                {
                    "id": str(grant.id),
                    "title": grant.title,
                    "agency": grant.data_source.agency.name,
                    "datasource": grant.data_source.name,
                    "amount": grant.amount,
                    "endDate": grant.end_date.strftime("%Y-%m-%d"),
                    "description": grant.description,
                }
                for grant in grants
            ]

            return jsonify(results)

    except Exception as e:
        logging.error(f"Stack trace:\n{traceback.format_exc()}")
        logging.error(f"Error getting grants by text: {str(e)}")
        return jsonify({"error": "Failed to get grants"}), 500


@api.route("/grants", methods=["GET"])
def get_grants():
    """Get grants filtered by agency and datasource"""
    try:
        # Get filter parameters from query string
        agency = request.args.get("agency", "")
        datasource = request.args.get("datasource", "")

        with get_session() as session:

            query = filter_grants_query(
                session,
                agency_id=agency,
                datasource_id=[datasource] if datasource else None,
            )

            # Order by due date descending
            query = query.order_by(desc(Grant.end_date))
            grants = [
                {
                    "id": str(grant.id),
                    "title": grant.title,
                    "agency": grant.data_source.agency.name,
                    "datasource": grant.data_source.name,
                    "amount": grant.amount,
                    "endDate": grant.end_date.strftime("%Y-%m-%d"),
                    "description": grant.description,
                }
                for grant in query.all()
            ]

            return jsonify(grants)

    except Exception as e:
        logging.error(f"Stack trace:\n{traceback.format_exc()}")
        logging.error(f"Error getting grants: {str(e)}")
        return jsonify({"error": "Failed to get grants"}), 500
