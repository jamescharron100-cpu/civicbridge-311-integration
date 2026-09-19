from .nyc311_client import fetch_complaints
from .normalizer import normalize_complaint
from .matcher import find_matching_property
from .properties import PROPERTIES
from .mapper import map_complaint
from .soap_client import send_maintenance_request
from .sync_store import initialize_sync_database, record_success, should_skip_record


def run_integration(endpoint_url: str, sync_db_path: str, limit: int = 10, bbl: str | None = None) -> dict[str, int]:
    initialize_sync_database(sync_db_path)
    raw_complaints = fetch_complaints(limit, bbl=bbl)

    summary = {
        "fetched": len(raw_complaints),
        "unmatched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
    }

    for raw_complaint in raw_complaints:
        complaint = normalize_complaint(raw_complaint)
        if should_skip_record(sync_db_path, complaint.source_id, complaint.source_updated_at):
            summary["skipped"] += 1
            continue

        matched_property = find_matching_property(complaint, PROPERTIES)
        if matched_property is None:
            summary["unmatched"] += 1
            continue

        request = map_complaint(complaint, matched_property)

        result = send_maintenance_request(request, endpoint_url)
        if result == "CREATED":
            summary["created"] += 1
        else:
            summary["updated"] += 1

        record_success(sync_db_path, complaint.source_id, complaint.source_updated_at, result)

    return summary


def main() -> None:
    summary = run_integration("http://127.0.0.1:8000/soap", "civicbridge_sync.db", limit=10, bbl=PROPERTIES[0].bbl)
    print(summary)


if __name__ == "__main__":
    main()
