from .nyc311_client import fetch_complaints
from .normalizer import normalize_complaint
from .matcher import find_matching_property
from .properties import PROPERTIES
from .mapper import map_complaint
from .soap_client import send_maintenance_request


def run_integration(endpoint_url: str, limit: int = 10, bbl: str | None = None) -> dict[str, int]:
    raw_complaints = fetch_complaints(limit, bbl=bbl)

    summary = {
        "fetched": len(raw_complaints),
        "unmatched": 0,
        "created": 0,
        "updated": 0,
    }

    for raw_complaint in raw_complaints:
        complaint = normalize_complaint(raw_complaint)

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

    return summary


def main() -> None:
    summary = run_integration("http://127.0.0.1:8000/soap", limit=10, bbl=PROPERTIES[0].bbl)
    print(summary)


if __name__ == "__main__":
    main()
