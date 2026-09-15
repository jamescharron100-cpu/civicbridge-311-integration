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

def fetch_complaints(limit: int = 10) -> list[dict[str, Any]]:
    quoted_types = ", ".join(f"'{complaint_type}'" for complaint_type in SUPPORTED_COMPLAINT_TYPES)

    params = {
        "$limit": limit,
        "$order": "created_date DESC",
        "$where": f"complaint_type IN ({quoted_types})",
        "$select": ", ".join(SOURCE_FIELDS)
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return data