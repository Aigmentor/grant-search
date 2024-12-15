from datetime import datetime, timedelta
from functools import wraps
import logging
import os
from threading import Thread
import traceback
from flask import Blueprint, jsonify, request, session
from sqlalchemy import desc

from grant_search.ai.query_processor import create_query
from grant_search.db.models import Grant, Agency, DataSource, GrantSearchQuery, User
from grant_search.db.database import get_session
from grant_search.ai.filter_string_to_function import query_by_text
from grant_search.filter_grants import filter_grants_query
from grant_search.ingest.ingest import Ingester

# XHR API for web app
api = Blueprint("api", __name__)


def check_auth():
    if not session.get("user") and request.endpoint != "api.auth_status":
        return jsonify({"error": "Not authorized"}), 401


# Apply login_required decorator to all routes
api.before_request(check_auth)


@api.route("/upload_datasource", methods=["POST"])
def upload_datasource():
    """Create a new datasource from form parameters"""
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "Missing request data"}), 400

    name = request_data.get("name")
    agency_name = request_data.get("agency")
    input_url = request_data.get("sourceUrl")

    if not name or not agency_name:
        return jsonify({"error": "Missing required fields"}), 400

    ingester = Ingester(source_name=name, agency=agency_name, source=input_url)
    Thread(target=ingester.ingest).start()

    return jsonify({"success": True}), 200


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
    """Sends grants filtered by natural language text description for processing"""
    # Get text from request body
    request_data = request.get_json()
    if not request_data or "text" not in request_data:
        return jsonify({"error": "Missing text parameter"}), 400

    text = request_data["text"]

    with get_session() as db_session:
        user = (
            db_session.query(User)
            .filter(User.email == session.get("user_email"))
            .first()
        )
        # Query grants using the text filter
        query_id = create_query(text, user)
        return jsonify({"queryId": query_id})


def json_for_query(query, start_index):
    if query.reasons is None and not query.complete:
        results = []
    elif query.reasons is None or len(query.reasons) == 0:
        results = []
    else:
        results = zip(query.grants, query.reasons)

    output = []
    # Skip entries before start_index
    results = list(results)[start_index:]
    for result in results:
        grant, reason = result
        data_source = grant.data_source
        output.append(
            {
                "id": str(grant.id),
                "title": grant.title,
                "agency": data_source.agency.name,
                "datasource": data_source.name,
                "amount": grant.amount,
                "endDate": grant.end_date.strftime("%Y-%m-%d"),
                "description": grant.description,
                "reason": reason,
                "awardUrl": grant.get_award_url(),
            }
        )

    return {
        "status": "success" if query.complete else query.status,
        "sampleFraction": query.sampling_fraction,
        "queryText": query.query_text,
        "results": output,
    }


@api.route("/grants_query_status", methods=["POST"])
def get_grants_query_status():
    request_data = request.get_json()
    if not request_data or "queryId" not in request_data:
        return jsonify({"error": "Missing queryId parameter"}), 400

    start_index = request_data.get("startIndex", 0)

    with get_session() as session:
        query = (
            session.query(GrantSearchQuery)
            .populate_existing()
            .get(request_data["queryId"])
        )
        if query is None:
            return jsonify({"error": f"No such query: {request_data['queryId']}"}), 400

        if not query.complete and query.timestamp < datetime.now() - timedelta(
            seconds=75
        ):
            query.status = "timed_out"
            session.commit()
            session.refresh(query)

        return jsonify(json_for_query(query, start_index)), 200


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
                datasource_ids=[datasource] if datasource else None,
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


@api.route("/user_status", methods=["GET"])
def auth_status():
    """Get current user's authentication status"""
    try:
        is_authenticated = "user" in session
        return jsonify(
            {
                "loggedIn": is_authenticated,
                "userEmail": session.get("user_email"),
                "username": session.get("username"),
            }
        )
    except Exception as e:
        logging.error(f"Error checking auth status: {str(e)}")
        return jsonify({"error": "Failed to check authentication status"}), 500


@api.route("/user_searches", methods=["GET"])
def get_user_searches():
    """Get saved searches for current user"""
    try:
        if "user_email" not in session:
            return jsonify({"error": "User not authenticated"}), 401

        with get_session() as db_session:
            user = (
                db_session.query(User)
                .filter(User.email == session.get("user_email"))
                .first()
            )

            searches = (
                db_session.query(GrantSearchQuery)
                .filter(GrantSearchQuery.user_id == user.id)
                .order_by(desc(GrantSearchQuery.created_at))
                .all()
            )

            return jsonify(
                [
                    {
                        "id": str(search.id),
                        "query": search.query,
                        "created_at": search.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    for search in searches
                ]
            )

    except Exception as e:
        logging.error(f"Error getting user searches: {str(e)}")
        return jsonify({"error": "Failed to get user searches"}), 500
