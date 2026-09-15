from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Complaint:
    source_id: str
    created_at: datetime
    agency: str
    complaint_type: str
    status: str
    source_updated_at: datetime

    closed_at: datetime | None = None
    descriptor: str | None = None
    incident_address: str | None = None
    incident_zip: str | None = None
    bbl: str | None = None
    borough: str | None = None


@dataclass(frozen=True)
class Property:
    property_id: str
    name: str
    address: str
    borough: str

    bbl: str | None = None
