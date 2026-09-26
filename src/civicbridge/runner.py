import logging

from .mapper import map_complaint
from .matcher import find_matching_property
from .normalizer import normalize_complaint
from .nyc311_client import fetch_complaint_pages
from .properties import PROPERTIES
from .soap_client import send_maintenance_request
from .sync_store import (
    finish_run,
    get_last_successful_run_started_at,
    initialize_sync_database,
    record_success,
    should_skip_record,
    start_run,
)

logger = logging.getLogger(__name__)


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
    logger.info(
        "event=integration_run_started "
        "run_id=%s checkpoint=%s page_size=%s max_pages=%s bbl=%s",
        run_id,
        updated_after.isoformat() if updated_after is not None else None,
        page_size,
        max_pages,
        bbl,
    )
    try:
        raw_complaints = fetch_complaint_pages(page_size=page_size, max_pages=max_pages, bbl=bbl, updated_after=updated_after)
        summary["fetched"] = len(raw_complaints)
        logger.info(
            "event=complaints_fetched run_id=%s count=%s",
            run_id,
            summary["fetched"],
        )

        for raw_complaint in raw_complaints:
            complaint = normalize_complaint(raw_complaint)
            if should_skip_record(sync_db_path, complaint.source_id, complaint.source_updated_at):
                summary["skipped"] += 1
                logger.info(
                    "event=complaint_skipped run_id=%s source_id=%s",
                    run_id,
                    complaint.source_id,
                )
                continue

            matched_property = find_matching_property(complaint, PROPERTIES)
            if matched_property is None:
                summary["unmatched"] += 1
                logger.info(
                    "event=complaint_unmatched run_id=%s source_id=%s",
                    run_id,
                    complaint.source_id,
                )
                continue

            request = map_complaint(complaint, matched_property)

            result = send_maintenance_request(request, endpoint_url)
            if result == "CREATED":
                summary["created"] += 1
            else:
                summary["updated"] += 1

            record_success(sync_db_path, complaint.source_id, complaint.source_updated_at, result)
            logger.info(
                "event=complaint_synchronized run_id=%s source_id=%s result=%s",
                run_id,
                complaint.source_id,
                result,
            )

        finish_run(sync_db_path, run_id, "SUCCEEDED", summary)
        logger.info(
            "event=integration_run_succeeded "
            "run_id=%s fetched=%s unmatched=%s created=%s updated=%s skipped=%s",
            run_id,
            summary["fetched"],
            summary["unmatched"],
            summary["created"],
            summary["updated"],
            summary["skipped"],
        )
        return summary
    except Exception as error:
        logger.exception(
            "event=integration_run_failed "
            "run_id=%s error_type=%s",
            run_id,
            type(error).__name__,
        )
        finish_run(sync_db_path, run_id, "FAILED", summary, str(error))
        raise


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s level=%(levelname)s "
            "logger=%(name)s %(message)s"
        ),
    )
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
