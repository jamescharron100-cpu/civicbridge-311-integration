from .models import Complaint, Property


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None

    return " ".join(value.upper().split())


def find_matching_property(complaint: Complaint, properties: list[Property]) -> Property | None:
    if complaint.bbl:
        for candidate in properties:
            if candidate.bbl == complaint.bbl:
                return candidate

    complaint_address = normalize_text(complaint.incident_address)
    complaint_borough = normalize_text(complaint.borough)

    if complaint_address and complaint_borough:
        for candidate in properties:
            if (
                normalize_text(candidate.address) == complaint_address
                and normalize_text(candidate.borough) == complaint_borough
            ):
                return candidate

    return None
