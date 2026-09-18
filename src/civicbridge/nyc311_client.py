from typing import Any
import requests


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


def fetch_complaints(limit: int = 10, bbl: str | None = None) -> list[dict[str, Any]]:
    quoted_types = ", ".join(f"'{complaint_type}'" for complaint_type in SUPPORTED_COMPLAINT_TYPES)
    where_clause = f"complaint_type IN ({quoted_types})"

    if bbl is not None:
        if bbl.isascii() and bbl.isdigit() and len(bbl) == 10:
            where_clause += f" AND bbl = '{bbl}'"
        else:
            raise ValueError("BBL must contain exactly 10 digits")

    params = {
        "$limit": limit,
        "$order": "created_date DESC",
        "$where": where_clause,
        "$select": ", ".join(SOURCE_FIELDS)
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return data
