from .nyc311_client import fetch_complaint_pages
from .normalizer import normalize_complaint
from .matcher import find_matching_property
from .properties import PROPERTIES
from .mapper import map_complaint
from .soap_client import send_maintenance_request
from .sync_store import initialize_sync_database, record_success, should_skip_record, start_run, finish_run, get_last_successful_run_started_at


def run_integration(
    endpoint_url: str,
    sync_db_path: str,
    page_size: int = 100,
    max_pages: int = 5,
    bbl: str | None = None,
) -> dict[str, int]:
    initialize_sync_database(sync_db_path)
    updated_after = get_last_successful_run_started_at(sync_db_path)

    summary = {
        "fetched": 0,
        "unmatched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
    }

    run_id = start_run(sync_db_path)
    try:
        raw_complaints = fetch_complaint_pages(page_size=page_size, max_pages=max_pages, bbl=bbl, updated_after=updated_after)
        summary["fetched"] = len(raw_complaints)

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

        finish_run(sync_db_path, run_id, "SUCCEEDED", summary)
        return summary
    except Exception as error:
        finish_run(sync_db_path, run_id, "FAILED", summary, str(error))
        raise


def main() -> None:
    summary = run_integration(
        "http://127.0.0.1:8000/soap",
        "civicbridge_sync.db",
        page_size=10,
        max_pages=3,
        bbl=PROPERTIES[0].bbl,
    )
    print(summary)


if __name__ == "__main__":
    main()
