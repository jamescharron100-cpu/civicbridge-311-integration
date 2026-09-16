from .models import Complaint, Property, MaintenanceRequest


CATEGORY_MAP = {
    "HEAT/HOT WATER": "HEATING",
    "PLUMBING": "PLUMBING",
    "ELEVATOR": "ELEVATOR",
}

PRIORITY_MAP = {
    "HEAT/HOT WATER": "HIGH",
    "PLUMBING": "NORMAL",
    "ELEVATOR": "HIGH",
}

STATUS_MAP = {
    "Open": "OPEN",
    "Closed": "CLOSED",
}


def map_complaint(complaint: Complaint, matched_property: Property) -> MaintenanceRequest:
    if complaint.complaint_type not in CATEGORY_MAP:
        raise ValueError(f"Unsupported complaint type: {complaint.complaint_type}")
    if complaint.status not in STATUS_MAP:
        raise ValueError(f"Unsupported complaint status: {complaint.status}")

    category = CATEGORY_MAP[complaint.complaint_type]
    priority = PRIORITY_MAP[complaint.complaint_type]
    status = STATUS_MAP[complaint.status]

    description = complaint.complaint_type
    if complaint.descriptor:
        description += f": {complaint.descriptor}"

    return MaintenanceRequest(
        external_id=complaint.source_id,
        property_id=matched_property.property_id,
        category=category,
        priority=priority,
        status=status,
        description=description,
        reported_at=complaint.created_at,
        source_updated_at=complaint.source_updated_at,
    )
