from typing import Any
from datetime import datetime
from .models import Complaint


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    return datetime.fromisoformat(value)


def normalize_complaint(raw: dict[str, Any]) -> Complaint:
    source_updated_raw = raw.get("resolution_action_updated_date") or raw.get("closed_date") or raw["created_date"]
    created_at = datetime.fromisoformat(raw["created_date"])
    source_updated_at = datetime.fromisoformat(source_updated_raw)

    return Complaint(
        source_id=raw["unique_key"],
        created_at=created_at,
        agency=raw["agency"],
        complaint_type=raw["complaint_type"],
        status=raw["status"],
        source_updated_at=source_updated_at,
        closed_at=parse_datetime(raw.get("closed_date")),
        descriptor=raw.get("descriptor"),
        incident_address=raw.get("incident_address"),
        incident_zip=raw.get("incident_zip"),
        bbl=raw.get("bbl"),
        borough=raw.get("borough")
    )


def normalize_complaints(raw_complaints: list[dict[str, Any]]) -> list[Complaint]:
    return [
        normalize_complaint(raw_complaint)
        for raw_complaint in raw_complaints
    ]
