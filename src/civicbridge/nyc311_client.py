from typing import Any
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


BASE_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

SUPPORTED_COMPLAINT_TYPES = (
    "HEAT/HOT WATER",
    "PLUMBING",
    "ELEVATOR"
)

SOURCE_FIELDS = (
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "descriptor",
    "incident_address",
    "incident_zip",
    "bbl",
    "borough",
    "status",
    "resolution_action_updated_date"
)


def fetch_complaints(
    limit: int = 10,
    bbl: str | None = None,
    offset: int = 0,
    updated_after: datetime | None = None,
) -> list[dict[str, Any]]:
    
    quoted_types = ", ".join(f"'{complaint_type}'" for complaint_type in SUPPORTED_COMPLAINT_TYPES)
    where_clause = f"complaint_type IN ({quoted_types})"

    if bbl is not None:
        if bbl.isascii() and bbl.isdigit() and len(bbl) == 10:
            where_clause += f" AND bbl = '{bbl}'"
        else:
            raise ValueError("BBL must contain exactly 10 digits")

    if limit <= 0:
        raise ValueError("Limit must be greater than zero")
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    
    if updated_after is not None:
        if updated_after.tzinfo is None or updated_after.utcoffset() is None:
            raise ValueError("Updated after must include timezone information")
        source_updated_after = (
            updated_after.astimezone(ZoneInfo("America/New_York"))
            .replace(tzinfo=None)
            .isoformat(timespec="seconds")
        )

        where_clause += (
            " AND coalesce("
            "resolution_action_updated_date, "
            "closed_date, "
            "created_date"
            f") > '{source_updated_after}'"
        )

    params = {
        "$limit": limit,
        "$order": "coalesce(resolution_action_updated_date, closed_date, created_date) DESC, unique_key DESC",
        "$where": where_clause,
        "$select": ", ".join(SOURCE_FIELDS),
        "$offset": offset,
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return data


def fetch_complaint_pages(
    page_size: int = 100,
    max_pages: int = 5,
    bbl: str | None = None,
) -> list[dict[str, Any]]:

    if page_size <= 0:
        raise ValueError("Page size must be greater than zero")
    if max_pages <= 0:
        raise ValueError("Max pages must be greater than zero")

    complaints = []
    for page_number in range(max_pages):
        offset = page_number * page_size
        page = fetch_complaints(limit=page_size, bbl=bbl, offset=offset)
        complaints.extend(page)

        if len(page) < page_size:
            break

    return complaints
