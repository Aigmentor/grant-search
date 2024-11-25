from datetime import datetime
from typing import List, Optional
from sqlalchemy import and_
from sqlalchemy.orm import Query, undefer

from grant_search.db.models import Agency, Grant, DataSource


def filter_grants_query(
    session,
    start_date_before: Optional[datetime] = None,
    start_date_after: Optional[datetime] = None,
    agency_id: Optional[int] = None,
    datasource_ids: Optional[list[int]] = None,
) -> Query:
    """
    Filter grants query by date range, agency and datasource

    Args:
        query: Base SQLAlchemy query object
        agency_id: Optional agency ID to filter by
        datasource_ids: Optional list of datasource IDs to filter by

    Returns:
        Filtered SQLAlchemy query
    """
    query = session.query(Grant).options(undefer(Grant.raw_text))

    if start_date_before:
        query = query.filter(Grant.start_date <= start_date_before)

    if start_date_before:
        query = query.filter(Grant.start_date >= start_date_after)

    # Join with DataSource if we need to filter by agency
    if agency_id:
        query = query.join(DataSource, Grant.data_source_id == DataSource.id)
        query = query.filter(DataSource.agency_id == agency_id)

    if datasource_ids and len(datasource_ids) > 0:
        query = query.filter(Grant.data_source_id in datasource_ids)

    return query
